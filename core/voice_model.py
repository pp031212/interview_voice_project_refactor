from funasr import AutoModel

from core.config import get_config

conf = get_config()

my_voice_model = AutoModel(
    model=conf.voice_model_path,
    trust_remote_code=True,
    vad_model=conf.voice_vad_model_path,
    vad_kwargs={"max_single_segment_time": 30000},
    device="cpu",
    disable_update=True,
)
