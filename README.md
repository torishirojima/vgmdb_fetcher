# VGMdb Fetcher

爬取vgmdb专辑详情页的专辑信息，并将专辑信息写入本地专辑音频文件中

## 简介

需要的Python版本为`3.11`，运行项目前先在config.cfg中进行配置，其中`REMOTE_ALBUM_URL`以及`LOCAL_ALBUM_SRC`是必填项，其他选项自行调整

## 安装依赖

```shell

pip install -r requirements.txt
```

## 运行

```shell

python fetcher.py
```

## config.cfg

抓取以及修改信息配置

## 对于本地专辑音频的文件的存放规定

如果您想要将vgmdb爬取到的专辑信息与本地的音频正确的匹配并写入，您的本地专辑文件必须符合以下要求

- 如果此专辑包含N张碟片(Disc)，则在本地专辑目录下面建立`Disc 1, Disc 2, ..., Disc N`N个目录，将对应碟片的音频文件放入
- 如果此专辑仅有1张碟片，则您可以直接将所有音频文件放入本地专辑目录下（当然也可以建一个`Disc 1`目录然后放入）
- 每个音频文件需要您提前编辑好该音频所在碟片的音轨号
