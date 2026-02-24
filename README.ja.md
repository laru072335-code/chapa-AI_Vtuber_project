# AI_Vtuber_project

## インストール方法
 (現在サポートしていません。自分のパソコンで動かしたい場合は環境構築の項目を参照してください。)

## 概要説明
### 自作のAIVtuberのソースコードです。
- 現在、コメント取得と発話ができます。
- 字幕表示機能やリップシンクも搭載されています。

## 環境
### python側
mamba環境でaienv_for_create.ymlを参照。
### Unity側
バージョン6000.2.7f2を使っています。
NativeWedSocketとNuget、MessagePackを使用。
また、シェーダーとしてlilToonを使用。
### その他
- わんコメを使用してコメントを取得している。
- ローカルLLMとして、ollama上で、dsasai/llama3-elyza-jp-8bを使用している。
- 興味推定の目的でgoogle search APIも導入している。
- VOICEVOXを使用して発話を制御している。

##環境構築方法
- 1,OneComme VOICEVOX をダウンロードしてください。
- 2,brewなどで、ollamaを導入して、mamba環境をaienv_for_create.ymlを参照して構築してください。
- 3,releasesにある、unity側のプログラムをダウンロードしてください。また、pythonブランチのfor_install.zipをダウンロードしてください。
- 4,


