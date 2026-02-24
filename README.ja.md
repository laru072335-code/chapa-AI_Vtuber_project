# AI_Vtuber_project

## インストール方法
 (現在サポートしていません。自分のパソコンで動かしたい場合は環境構築の項目を参照してください。)

## 概要説明
### 自作のAIVtuberのソースコードです。
- 現在、コメント取得と発話ができます。
- 字幕表示機能やリップシンクも搭載されています。
- 現在、macにしか対応していません。

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
- 2,brewなどで、ollamaを導入して、dsasai/llama3-elyza-jp-8bをインストールしてください。
- 3,環境をaienv_for_create.ymlを参照して構築してください。
- 4,releasesにある、unity側のプログラム(virtual_AI_roid0.1(alpha))をダウンロードしてください。また、pythonブランチのfor_install.zipをダウンロードしてください。

## 起動方法
-1,OneComme,VOICEVOXを起動してください。
-2,OneCommeのコメントテスター機能を使って、コメントを何か追加してください。
-3,for_installの中にある、AI_Vtuber_core_for_steam_voicevox_version.pyを環境項目で示した環境で実行してください。
-4,unity側のvirtual_AI_roid0.1(alpha)を起動してください。(こちらをAI_Vtuber_core_for_steam_voicevox_version.pyより先に起動すると動きません)

## 注意事項
-このプロジェクトは開発途中であるので、さまざまなバグなどが残っている可能性があります。

## テスト環境
- macbook air m4 RAM 16GB

