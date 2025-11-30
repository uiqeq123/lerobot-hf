<p align="center">
  <img alt="LeRobot, Hugging Face Robotics Library" src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/lerobot-logo-thumbnail.png" width="100%">
  <br/>
  <br/>
</p>

<div align="center">

[![Tests](https://github.com/huggingface/lerobot/actions/workflows/nightly.yml/badge.svg?branch=main)](https://github.com/huggingface/lerobot/actions/workflows/nightly.yml?query=branch%3Amain)
[![Python versions](https://img.shields.io/pypi/pyversions/lerobot)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/huggingface/lerobot/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/lerobot)](https://pypi.org/project/lerobot/)
[![Version](https://img.shields.io/pypi/v/lerobot)](https://pypi.org/project/lerobot/)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.1-ff69b4.svg)](https://github.com/huggingface/lerobot/blob/main/CODE_OF_CONDUCT.md)
[![Discord](https://dcbadge.vercel.app/api/server/C5P34WJ68S?style=flat)](https://discord.gg/s3KuuzsPFb)

<!-- [![Coverage](https://codecov.io/gh/huggingface/lerobot/branch/main/graph/badge.svg?token=TODO)](https://codecov.io/gh/huggingface/lerobot) -->

</div>

<h2 align="center">
    <p><a href="https://huggingface.co/docs/lerobot/hope_jr">
        Build Your Own HopeJR Robot!</a></p>
</h2>

<div align="center">
  <img
    src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/hope_jr/hopejr.png"
    alt="HopeJR robot"
    title="HopeJR robot"
    width="60%"
  />

  <p><strong>Meet HopeJR – A humanoid robot arm and hand for dexterous manipulation!</strong></p>
  <p>Control it with exoskeletons and gloves for precise hand movements.</p>
  <p>Perfect for advanced manipulation tasks! 🤖</p>

  <p><a href="https://huggingface.co/docs/lerobot/hope_jr">
      See the full HopeJR tutorial here.</a></p>
</div>

<br/>

<h2 align="center">
    <p><a href="https://huggingface.co/docs/lerobot/so101">
        Build Your Own SO-101 Robot!</a></p>
</h2>

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/so101/so101.webp" alt="SO-101 follower arm" title="SO-101 follower arm" width="90%"/></td>
      <td align="center"><img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/so101/so101-leader.webp" alt="SO-101 leader arm" title="SO-101 leader arm" width="90%"/></td>
    </tr>
  </table>

  <p><strong>Meet the updated SO100, the SO-101 – Just €114 per arm!</strong></p>
  <p>Train it in minutes with a few simple moves on your laptop.</p>
  <p>Then sit back and watch your creation act autonomously! 🤯</p>

  <p><a href="https://huggingface.co/docs/lerobot/so101">
      See the full SO-101 tutorial here.</a></p>

  <p>Want to take it to the next level? Make your SO-101 mobile by building LeKiwi!</p>
  <p>Check out the <a href="https://huggingface.co/docs/lerobot/lekiwi">LeKiwi tutorial</a> and bring your robot to life on wheels.</p>

  <img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/lekiwi/kiwi.webp" alt="LeKiwi mobile robot" title="LeKiwi mobile robot" width="50%">
</div>

<br/>

<h3 align="center">
    <p>LeRobot: State-of-the-art AI for real-world robotics</p>
</h3>

---

🤗 LeRobot aims to provide models, datasets, and tools for real-world robotics in PyTorch. The goal is to lower the barrier to entry to robotics so that everyone can contribute and benefit from sharing datasets and pretrained models.

🤗 LeRobot contains state-of-the-art approaches that have been shown to transfer to the real-world with a focus on imitation learning and reinforcement learning.

🤗 LeRobot already provides a set of pretrained models, datasets with human collected demonstrations, and simulation environments to get started without assembling a robot. In the coming weeks, the plan is to add more and more support for real-world robotics on the most affordable and capable robots out there.

🤗 LeRobot hosts pretrained models and datasets on this Hugging Face community page: [huggingface.co/lerobot](https://huggingface.co/lerobot)

#### Examples of pretrained models on simulation environments

<table>
  <tr>
    <td><img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/gym/aloha_act.gif" width="100%" alt="ACT policy on ALOHA env"/></td>
    <td><img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/gym/simxarm_tdmpc.gif" width="100%" alt="TDMPC policy on SimXArm env"/></td>
    <td><img src="https://raw.githubusercontent.com/huggingface/lerobot/main/media/gym/pusht_diffusion.gif" width="100%" alt="Diffusion policy on PushT env"/></td>
  </tr>
  <tr>
    <td align="center">ACT policy on ALOHA env</td>
    <td align="center">TDMPC policy on SimXArm env</td>
    <td align="center">Diffusion policy on PushT env</td>
  </tr>
</table>

## Installation

LeRobot works with Python 3.10+ and PyTorch 2.2+.

### Environment Setup

Create a virtual environment with Python 3.10 and activate it, e.g. with [`miniforge`](https://conda-forge.org/download/):

```bash
conda create -y -n lerobot python=3.10
conda activate lerobot
```

When using `conda`, install `ffmpeg` in your environment:

```bash
conda install ffmpeg -c conda-forge
```

> **NOTE:** This usually installs `ffmpeg 7.X` for your platform compiled with the `libsvtav1` encoder. If `libsvtav1` is not supported (check supported encoders with `ffmpeg -encoders`), you can:
>
> - _[On any platform]_ Explicitly install `ffmpeg 7.X` using:
>
> ```bash
> conda install ffmpeg=7.1.1 -c conda-forge
> ```
>
> - _[On Linux only]_ Install [ffmpeg build dependencies](https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu#GettheDependencies) and [compile ffmpeg from source with libsvtav1](https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu#libsvtav1), and make sure you use the corresponding ffmpeg binary to your install with `which ffmpeg`.

### Install LeRobot 🤗

#### From Source

First, clone the repository and navigate into the directory:

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
```

Then, install the library in editable mode. This is useful if you plan to contribute to the code.

```bash
pip install -e .
```

> **NOTE:** If you encounter build errors, you may need to install additional dependencies (`cmake`, `build-essential`, and `ffmpeg libs`). On Linux, run:
> `sudo apt-get install cmake build-essential python3-dev pkg-config libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev`. For other systems, see: [Compiling PyAV](https://pyav.org/docs/develop/overview/installation.html#bring-your-own-ffmpeg)

For simulations, 🤗 LeRobot comes with gymnasium environments that can be installed as extras:

- [aloha](https://github.com/huggingface/gym-aloha)
- [xarm](https://github.com/huggingface/gym-xarm)
- [pusht](https://github.com/huggingface/gym-pusht)

For instance, to install 🤗 LeRobot with aloha and pusht, use:

```bash
pip install -e ".[aloha, pusht]"
```

### Installation from PyPI

**Core Library:**
Install the base package with:

```bash
pip install lerobot
```

_This installs only the default dependencies._

**Extra Features:**
To install additional functionality, use one of the following:

```bash
pip install 'lerobot[all]'          # All available features
pip install 'lerobot[aloha,pusht]'  # Specific features (Aloha & Pusht)
pip install 'lerobot[feetech]'      # Feetech motor support
```

_Replace `[...]` with your desired features._

**Available Tags:**
For a full list of optional dependencies, see:
https://pypi.org/project/lerobot/

> [!NOTE]
> For lerobot 0.4.0, if you want to install libero or pi tags, you will have to do: `pip install "lerobot[pi,libero]@git+https://github.com/huggingface/lerobot.git"`.
>
> This will be solved in the next patch release

### Weights & Biases

To use [Weights and Biases](https://docs.wandb.ai/quickstart) for experiment tracking, log in with

```bash
wandb login
```

(note: you will also need to enable WandB in the configuration. See below.)

### Visualize datasets

Check out [example 1](https://github.com/huggingface/lerobot/blob/main/examples/dataset/load_lerobot_dataset.py) that illustrates how to use our dataset class which automatically downloads data from the Hugging Face hub.

You can also locally visualize episodes from a dataset on the hub by executing our script from the command line:

```bash
lerobot-dataset-viz \
    --repo-id lerobot/pusht \
    --episode-index 0
```

or from a dataset in a local folder with the `root` option and the `--mode local` (in the following case the dataset will be searched for in `./my_local_data_dir/lerobot/pusht`)

```bash
lerobot-dataset-viz \
    --repo-id lerobot/pusht \
    --root ./my_local_data_dir \
    --mode local \
    --episode-index 0
```

It will open `rerun.io` and display the camera streams, robot states and actions, like this:

https://github-production-user-asset-6210df.s3.amazonaws.com/4681518/328035972-fd46b787-b532-47e2-bb6f-fd536a55a7ed.mov?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAVCODYLSA53PQK4ZA%2F20240505%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20240505T172924Z&X-Amz-Expires=300&X-Amz-Signature=d680b26c532eeaf80740f08af3320d22ad0b8a4e4da1bcc4f33142c15b509eda&X-Amz-SignedHeaders=host&actor_id=24889239&key_id=0&repo_id=748713144

Our script can also visualize datasets stored on a distant server. See `lerobot-dataset-viz --help` for more instructions.

### The `LeRobotDataset` format

A dataset in `LeRobotDataset` format is very simple to use. It can be loaded from a repository on the Hugging Face hub or a local folder simply with e.g. `dataset = LeRobotDataset("lerobot/aloha_static_coffee")` and can be indexed into like any Hugging Face and PyTorch dataset. For instance `dataset[0]` will retrieve a single temporal frame from the dataset containing observation(s) and an action as PyTorch tensors ready to be fed to a model.

A specificity of `LeRobotDataset` is that, rather than retrieving a single frame by its index, we can retrieve several frames based on their temporal relationship with the indexed frame, by setting `delta_timestamps` to a list of relative times with respect to the indexed frame. For example, with `delta_timestamps = {"observation.image": [-1, -0.5, -0.2, 0]}` one can retrieve, for a given index, 4 frames: 3 "previous" frames 1 second, 0.5 seconds, and 0.2 seconds before the indexed frame, and the indexed frame itself (corresponding to the 0 entry). See example [1_load_lerobot_dataset.py](https://github.com/huggingface/lerobot/blob/main/examples/dataset/load_lerobot_dataset.py) for more details on `delta_timestamps`.

Under the hood, the `LeRobotDataset` format makes use of several ways to serialize data which can be useful to understand if you plan to work more closely with this format. We tried to make a flexible yet simple dataset format that would cover most type of features and specificities present in reinforcement learning and robotics, in simulation and in real-world, with a focus on cameras and robot states but easily extended to other types of sensory inputs as long as they can be represented by a tensor.

Here are the important details and internal structure organization of a typical `LeRobotDataset` instantiated with `dataset = LeRobotDataset("lerobot/aloha_static_coffee")`. The exact features will change from dataset to dataset but not the main aspects:

```
dataset attributes:
  ├ hf_dataset: a Hugging Face dataset (backed by Arrow/parquet). Typical features example:
  │  ├ observation.images.cam_high (VideoFrame):
  │  │   VideoFrame = {'path': path to a mp4 video, 'timestamp' (float32): timestamp in the video}
  │  ├ observation.state (list of float32): position of an arm joints (for instance)
  │  ... (more observations)
  │  ├ action (list of float32): goal position of an arm joints (for instance)
  │  ├ episode_index (int64): index of the episode for this sample
  │  ├ frame_index (int64): index of the frame for this sample in the episode ; starts at 0 for each episode
  │  ├ timestamp (float32): timestamp in the episode
  │  ├ next.done (bool): indicates the end of an episode ; True for the last frame in each episode
  │  └ index (int64): general index in the whole dataset
  ├ meta: a LeRobotDatasetMetadata object containing:
  │  ├ info: a dictionary of metadata on the dataset
  │  │  ├ codebase_version (str): this is to keep track of the codebase version the dataset was created with
  │  │  ├ fps (int): frame per second the dataset is recorded/synchronized to
  │  │  ├ features (dict): all features contained in the dataset with their shapes and types
  │  │  ├ total_episodes (int): total number of episodes in the dataset
  │  │  ├ total_frames (int): total number of frames in the dataset
  │  │  ├ robot_type (str): robot type used for recording
  │  │  ├ data_path (str): formattable string for the parquet files
  │  │  └ video_path (str): formattable string for the video files (if using videos)
  │  ├ episodes: a DataFrame containing episode metadata with columns:
  │  │  ├ episode_index (int): index of the episode
  │  │  ├ tasks (list): list of tasks for this episode
  │  │  ├ length (int): number of frames in this episode
  │  │  ├ dataset_from_index (int): start index of this episode in the dataset
  │  │  └ dataset_to_index (int): end index of this episode in the dataset
  │  ├ stats: a dictionary of statistics (max, mean, min, std) for each feature in the dataset, for instance
  │  │  ├ observation.images.front_cam: {'max': tensor with same number of dimensions (e.g. `(c, 1, 1)` for images, `(c,)` for states), etc.}
  │  │  └ ...
  │  └ tasks: a DataFrame containing task information with task names as index and task_index as values
  ├ root (Path): local directory where the dataset is stored
  ├ image_transforms (Callable): optional image transformations to apply to visual modalities
  └ delta_timestamps (dict): optional delta timestamps for temporal queries
```

A `LeRobotDataset` is serialised using several widespread file formats for each of its parts, namely:

- hf_dataset stored using Hugging Face datasets library serialization to parquet
- videos are stored in mp4 format to save space
- metadata are stored in plain json/jsonl files

Dataset can be uploaded/downloaded from the HuggingFace hub seamlessly. To work on a local dataset, you can specify its location with the `root` argument if it's not in the default `~/.cache/huggingface/lerobot` location.

#### Reproduce state-of-the-art (SOTA)

We provide some pretrained policies on our [hub page](https://huggingface.co/lerobot) that can achieve state-of-the-art performances.
You can reproduce their training by loading the config from their run. Simply running:

```bash
lerobot-train --config_path=lerobot/diffusion_pusht
```

reproduces SOTA results for Diffusion Policy on the PushT task.

## Contribute

If you would like to contribute to 🤗 LeRobot, please check out our [contribution guide](https://github.com/huggingface/lerobot/blob/main/CONTRIBUTING.md).

### Add a pretrained policy

Once you have trained a policy you may upload it to the Hugging Face hub using a hub id that looks like `${hf_user}/${repo_name}` (e.g. [lerobot/diffusion_pusht](https://huggingface.co/lerobot/diffusion_pusht)).

You first need to find the checkpoint folder located inside your experiment directory (e.g. `outputs/train/2024-05-05/20-21-12_aloha_act_default/checkpoints/002500`). Within that there is a `pretrained_model` directory which should contain:

- `config.json`: A serialized version of the policy configuration (following the policy's dataclass config).
- `model.safetensors`: A set of `torch.nn.Module` parameters, saved in [Hugging Face Safetensors](https://huggingface.co/docs/safetensors/index) format.
- `train_config.json`: A consolidated configuration containing all parameters used for training. The policy configuration should match `config.json` exactly. This is useful for anyone who wants to evaluate your policy or for reproducibility.

To upload these to the hub, run the following:

```bash
huggingface-cli upload ${hf_user}/${repo_name} path/to/pretrained_model
```

See [lerobot_eval.py](https://github.com/huggingface/lerobot/blob/main/src/lerobot/scripts/lerobot_eval.py) for an example of how other people may use your policy.

### Acknowledgment

- The LeRobot team 🤗 for building SmolVLA [Paper](https://arxiv.org/abs/2506.01844), [Blog](https://huggingface.co/blog/smolvla).
- Thanks to Tony Zhao, Zipeng Fu and colleagues for open sourcing ACT policy, ALOHA environments and datasets. Ours are adapted from [ALOHA](https://tonyzhaozh.github.io/aloha) and [Mobile ALOHA](https://mobile-aloha.github.io).
- Thanks to Cheng Chi, Zhenjia Xu and colleagues for open sourcing Diffusion policy, Pusht environment and datasets, as well as UMI datasets. Ours are adapted from [Diffusion Policy](https://diffusion-policy.cs.columbia.edu) and [UMI Gripper](https://umi-gripper.github.io).
- Thanks to Nicklas Hansen, Yunhai Feng and colleagues for open sourcing TDMPC policy, Simxarm environments and datasets. Ours are adapted from [TDMPC](https://github.com/nicklashansen/tdmpc) and [FOWM](https://www.yunhaifeng.com/FOWM).
- Thanks to Antonio Loquercio and Ashish Kumar for their early support.
- Thanks to [Seungjae (Jay) Lee](https://sjlee.cc/), [Mahi Shafiullah](https://mahis.life/) and colleagues for open sourcing [VQ-BeT](https://sjlee.cc/vq-bet/) policy and helping us adapt the codebase to our repository. The policy is adapted from [VQ-BeT repo](https://github.com/jayLEE0301/vq_bet_official).

## Citation

If you want, you can cite this work with:

```bibtex
@misc{cadene2024lerobot,
    author = {Cadene, Remi and Alibert, Simon and Soare, Alexander and Gallouedec, Quentin and Zouitine, Adil and Palma, Steven and Kooijmans, Pepijn and Aractingi, Michel and Shukor, Mustafa and Aubakirova, Dana and Russi, Martino and Capuano, Francesco and Pascal, Caroline and Choghari, Jade and Moss, Jess and Wolf, Thomas},
    title = {LeRobot: State-of-the-art Machine Learning for Real-World Robotics in Pytorch},
    howpublished = "\url{https://github.com/huggingface/lerobot}",
    year = {2024}
}
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=huggingface/lerobot&type=Timeline)](https://star-history.com/#huggingface/lerobot&Timeline)

# LeRobot ROSmaster 数据收集工具

本项目提供了用于ROSmaster机器人数据收集和操作的一套工具，可用于记录机器人操作数据、执行动作回放以及查看数据集信息。

## 工具列表

### 1. lerobot_rosmaster_data_collection.py

符合LeRobot标准数据格式的ROSmaster数据收集脚本。

#### 功能
- 记录leader机械臂的手动操作数据并保存为LeRobot标准数据集格式
- 执行follower机械臂的动作回放
- 查看已记录的数据文件内容

#### 使用方法
```bash
# 记录leader数据
python lerobot_rosmaster_data_collection.py record --episode-count 1 --episode-length 300

# 执行follower动作
python lerobot_rosmaster_data_collection.py execute <数据目录>

# 查看数据集信息
python lerobot_rosmaster_data_collection.py info <数据目录>
```

#### 特点
- 生成符合LeRobot标准的数据集格式
- 自动处理无效角度数据
- 确保关节角度在安全范围内
- 执行前进行功能测试和用户确认
- 同步采集摄像头图像数据

---

### 2. simple_rosmaster_data_collection.py

简化版ROSmaster数据收集脚本。

#### 功能
- 记录leader机械臂的手动操作数据
- 执行follower机械臂的动作回放
- 查看已记录的数据文件内容

#### 使用方法
```bash
# 记录leader数据 (默认30秒)
python simple_rosmaster_data_collection.py record

# 记录指定时长的leader数据
python simple_rosmaster_data_collection.py record 60

# 执行follower动作
python simple_rosmaster_data_collection.py execute <数据文件>

# 执行并记录follower动作
python simple_rosmaster_data_collection.py execute_and_record <数据文件>

# 查看数据文件
python simple_rosmaster_data_collection.py view <数据文件>
```

#### 特点
- 自动处理无效角度数据
- 确保关节角度在安全范围内
- 执行前进行功能测试和用户确认
- 同步采集摄像头图像数据

---

### 3. realtime_data_recorder.py

实时数据记录器，记录ROSmaster机器人的机械臂、小车和摄像头数据。

#### 功能
- 实时记录每一帧的机械臂角度数据
- 实时记录小车运动状态数据
- 定期获取并保存摄像头图像数据

#### 使用方法
```bash
# 开始实时记录数据 (按Ctrl+C停止)
python realtime_data_recorder.py record

# 指定时长记录数据
python realtime_data_recorder.py record --duration 60

# 查看已记录的数据
python realtime_data_recorder.py view --data-dir <数据目录路径>
```

#### 输出数据结构
```
realtime_recordings/
└── record_YYYYMMDD_HHMMSS/
    ├── recording_data.json     # 包含所有非图像数据的JSON文件
    └── images/
        ├── usb/               # USB摄像头图像
        │   ├── usb_frame_000000.jpg
        │   ├── usb_frame_000001.jpg
        │   └── ...
        └── depth/             # 深度摄像头图像
            ├── depth_frame_000000.jpg
            ├── depth_frame_000001.jpg
            └── ...
```

---

## 环境要求

- Python 3.8+
- 相关依赖包（参考requirements.txt）

## 使用注意事项

1. 确保机器人已开机并与电脑处于同一网络
2. 默认机器人IP地址为192.168.1.11，如有不同请使用--host参数指定
3. 确保有足够的磁盘空间存储图像数据
4. 在执行follower动作前，建议先进行功能测试确保设备正常工作

## 数据格式说明

### LeRobot数据集格式

LeRobot数据集遵循Hugging Face数据集格式，包含以下特征：
- `observation.joints`: 机械臂关节角度观测值
- `observation.joints_vel`: 机械臂关节速度观测值
- `observation.velocity`: 小车速度观测值[x_vel, y_vel, z_vel]
- `observation.images.usb`: USB摄像头图像（可选）
- `observation.images.depth`: 深度摄像头图像（可选）
- `action`: 动作数据，即机械臂关节角度目标值

### Simple数据格式

Simple数据格式为JSON文件，包含时间戳、机械臂角度和小车运动数据。

### Realtime数据格式

Realtime数据格式包含JSON元数据文件和图像文件，JSON文件记录每帧的时间戳、机械臂角度和小车运动数据，图像文件单独存储在目录中。
