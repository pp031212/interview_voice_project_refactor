# 本地语音模型下载与配置

本项目没有把模型文件提交到 GitHub。模型位于 `data/models/`，权重文件体积较大，且 `data/` 还会保存录音、切分音频、checkpoint 等运行数据，所以已被 `.gitignore` 忽略。

## 需要下载的模型

项目当前使用 FunASR 加载本地 ASR 模型，代码位置：`core/voice_model.py`。

需要准备两个模型：

| 用途 | ModelScope 模型 ID | 推荐本地目录 |
| --- | --- | --- |
| 语音识别 ASR | `iic/SenseVoiceSmall` | `data/models/SenseVoiceSmall` |
| 语音活动检测 VAD | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | `data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch` |

## 方式一：使用 ModelScope SDK 下载

先进入项目根目录：

```powershell
cd D:\PycharmProjects\interview_voice_project_refactor
```

安装依赖：

```powershell
pip install -r requirements.txt
```

创建模型目录：

```powershell
New-Item -ItemType Directory -Force data\models | Out-Null
```

下载 SenseVoiceSmall：

```powershell
python -c "from modelscope import snapshot_download; snapshot_download('iic/SenseVoiceSmall', local_dir='data/models/SenseVoiceSmall')"
```

下载 FSMN VAD：

```powershell
python -c "from modelscope import snapshot_download; snapshot_download('iic/speech_fsmn_vad_zh-cn-16k-common-pytorch', revision='v2.0.4', local_dir='data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch')"
```

如果你的 `modelscope` 版本不支持 `local_dir` 参数，先升级：

```powershell
pip install -U modelscope
```

## 方式二：使用 Git 下载

如果 SDK 下载不稳定，也可以直接从 ModelScope Git 仓库克隆：

```powershell
git clone https://www.modelscope.cn/iic/SenseVoiceSmall.git data/models/SenseVoiceSmall
git clone https://www.modelscope.cn/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch.git data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
```

## 配置 .env

复制 `.env.example` 为 `.env`，然后设置模型路径：

```env
VOICE_MODEL_PATH=data/models/SenseVoiceSmall
VOICE_VAD_MODEL_PATH=data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
```

这两个路径也可以写绝对路径，例如：

```env
VOICE_MODEL_PATH=D:/PycharmProjects/interview_voice_project_refactor/data/models/SenseVoiceSmall
VOICE_VAD_MODEL_PATH=D:/PycharmProjects/interview_voice_project_refactor/data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch
```

推荐使用相对路径，方便换机器后继续使用。

## 下载后目录检查

下载完成后，目录里至少应包含这些关键文件：

```text
data/models/SenseVoiceSmall/
  config.yaml
  configuration.json
  model.pt
  tokens.json
  chn_jpn_yue_eng_ko_spectok.bpe.model

data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch/
  config.yaml
  configuration.json
  model.pt
```

## 快速验证

在项目根目录执行：

```powershell
python -c "from core.voice_model import my_voice_model; print('voice_model_loaded')"
```

如果输出 `voice_model_loaded`，说明模型路径和依赖基本可用。

## 常见问题

1. `VOICE_MODEL_PATH` 或 `VOICE_VAD_MODEL_PATH` 为空  
   检查 `.env` 是否在项目根目录，且变量名没有写错。

2. `model.pt` 不存在  
   模型没有下载完整，删除对应模型目录后重新下载。

3. 下载很慢或中断  
   优先使用 ModelScope SDK；如果多次失败，改用 Git 下载。

4. GitHub 上看不到模型  
   这是预期行为。模型、录音、checkpoint、生成报告都在 `.gitignore` 中，不会提交到仓库。
