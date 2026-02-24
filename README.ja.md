# AI_Vtuber_project

## インストール方法
  -1 OneCommeと、VOICEVOXをインストールしてください。

## 概要説明
AIVtuberのソースコードです。
現在、コメント取得と発話ができます。

## 環境
### python側
mamba環境でaienv_for_create.ymlを参照。
### Unity側
NativeWedSocketとNuget、MessagePackを使用。
また、シェーダーとしてlilToonを使用。
### その他
- わんコメを使用してコメントを取得している。
- ローカルLLMとして、ollama上で、dsasai/llama3-elyza-jp-8bを使用している。
- 興味推定の目的でgoogle search APIも導入している。
- VOICEVOXを使用して発話を制御している。

##環境構築方法
