import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from funasr.utils.postprocess_utils import rich_transcription_postprocess
from tqdm import tqdm

from pipelines.agent_state import AgentState
from infra.update_mysql import update_mysql
from core.voice_model import my_voice_model
from core.utils.path_utils import get_file_path, to_project_relative_path
from core.errors import ASRError, FileNotFoundError as AppFileNotFoundError
from infra.db.db_helper import my_db_helper


async def void2text(voice_path):
    try:
        res = my_voice_model.generate(
            input=voice_path,
            cache={},
            language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,  #
            merge_length_s=15,
        )
        text = rich_transcription_postprocess(res[0]["text"])
        return text
    except Exception as exc:
        raise ASRError(f"语音识别失败: {str(exc)}")


def _get_asr_resume_path(record_id: int) -> Path:
    resume_dir = Path(get_file_path("data/checkpoints/asr_resume"))
    resume_dir.mkdir(parents=True, exist_ok=True)
    return resume_dir / f"record_{record_id}.json"


def _load_asr_resume_file_data(record_id: int, split_audio_path_list: list[str]) -> dict:
    resume_path = _get_asr_resume_path(record_id)
    if not resume_path.exists():
        return {"meta": {}, "results": {}}

    try:
        payload = json.loads(resume_path.read_text(encoding="utf-8"))
        results = payload.get("results", {})
        if not isinstance(results, dict):
            return {"meta": {}, "results": {}}

        # 若分片数量不一致，视为新任务，避免错误复用旧缓存。
        cached_count = payload.get("meta", {}).get("split_count")
        if cached_count != len(split_audio_path_list):
            return {"meta": {}, "results": {}}

        return {
            "meta": payload.get("meta", {}),
            "results": results,
        }
    except Exception:
        return {"meta": {}, "results": {}}


def _save_asr_resume_file_data(record_id: int, split_audio_path_list: list[str], results: dict) -> None:
    resume_path = _get_asr_resume_path(record_id)
    payload = {
        "meta": {
            "record_id": record_id,
            "split_count": len(split_audio_path_list),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "results": results,
    }
    temp_path = resume_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(resume_path)


def _clear_asr_resume_data(record_id: int) -> None:
    resume_path = _get_asr_resume_path(record_id)
    if resume_path.exists():
        resume_path.unlink()


def _load_asr_resume_db_data(record_id: int) -> dict:
    """从数据库加载 ASR 分片缓存。"""
    try:
        rows = my_db_helper.get_asr_segment_cache(record_id)
        results: dict[str, dict] = {}
        for row in rows:
            idx = row.get("segment_index")
            if idx is None:
                continue
            results[str(idx)] = {
                "path": to_project_relative_path(row.get("segment_path", "")),
                "text": row.get("segment_text", ""),
            }
        return results
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ 读取 ASR 分片缓存(DB)失败，将回退文件缓存: {exc}")
        return {}


def _upsert_asr_resume_db_data(record_id: int, segment_index: int, path: str, text: str) -> bool:
    """写入单个分片缓存到数据库。"""
    try:
        my_db_helper.upsert_asr_segment_cache(
            record_id=record_id,
            segment_index=segment_index,
            segment_path=path,
            segment_text=text,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ 写入 ASR 分片缓存(DB)失败，将仅保留文件缓存: {exc}")
        return False


def _clear_asr_resume_db_data(record_id: int) -> None:
    try:
        my_db_helper.clear_asr_segment_cache(record_id)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ 清理 ASR 分片缓存(DB)失败: {exc}")


def clear_asr_resume_cache(record_id: int) -> None:
    """在整条流程成功后清理 ASR 中间缓存。"""
    _clear_asr_resume_db_data(record_id)
    _clear_asr_resume_data(record_id)


async def voice_to_text_node(state: AgentState):
    await update_mysql("开始语音转文本", record_id=state["record_id"])
    split_audio_path_list = state['split_audio_path_list']

    # 混合持久化策略：DB 为主，文件为兜底
    resume_results = _load_asr_resume_db_data(state["record_id"])
    file_resume_data = _load_asr_resume_file_data(state["record_id"], split_audio_path_list)
    file_resume_results = file_resume_data["results"]
    if not resume_results and file_resume_results:
        resume_results = file_resume_results

    voice_text_list: list[str] = []
    total = len(split_audio_path_list)

    for i, split_audio_path in enumerate(tqdm(split_audio_path_list, desc="处理语音")):
        split_audio_relative_path = to_project_relative_path(split_audio_path)
        key = str(i)
        cached_item = resume_results.get(key, {})
        cached_path = to_project_relative_path(cached_item.get("path", ""))
        cached_text = cached_item.get("text", "")

        if cached_path == split_audio_relative_path and isinstance(cached_text, str) and cached_text:
            text = cached_text
            await update_mysql(
                f"正在处理第{(i + 1)}/{total}块（命中断点缓存，跳过识别）。",
                record_id=state["record_id"]
            )
        else:
            text = await void2text(split_audio_path)
            resume_results[key] = {"path": split_audio_relative_path, "text": text}
            _upsert_asr_resume_db_data(state["record_id"], i, split_audio_relative_path, text)
            _save_asr_resume_file_data(state["record_id"], split_audio_path_list, resume_results)
            await update_mysql(f"正在处理第{(i + 1)}/{total}块。", record_id=state["record_id"])

        print(text)
        voice_text_list.append(text)

    print(voice_text_list)
    state['voice_text_list'] = voice_text_list
    await update_mysql("完成语音转文本", record_id=state["record_id"])
    return state


if __name__ == '__main__':
    voice_to_text_node({"split_audio_path_list": [
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_001.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_002.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_003.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_004.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_005.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_006.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_007.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_008.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_009.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_010.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_011.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_012.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_013.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_014.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_015.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_016.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_017.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_018.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_019.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_020.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_021.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_022.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_023.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_024.wav',
        '/Users/duyi/PycharmProjects/interview_voice_project/voice/20250927_201420_罗培鑫面试/20250927_201420_罗培鑫面试_segment_025.wav']})
