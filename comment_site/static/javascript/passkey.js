
const { startRegistration, startAuthentication } = SimpleWebAuthnBrowser;
const BaseURL = 'https://chapa-api-three.vercel.app';//http://localhost:8000
// --------------------------------------------------------
// 1. パスキー登録
// --------------------------------------------------------
async function Register() {
    const username = document.getElementById("username").value;

    try {
        const resBegin = await fetch(`${BaseURL}/begin_register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const options = await resBegin.json();

        const attResp = await startRegistration(options);

        const resComplete = await fetch(`${BaseURL}/end_register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, credential: attResp })
        });
        const result = await resComplete.json();

        if (resComplete.ok) {
        }
        //statusEl.innerHTML = "<span style='color: green;'>✅ 登録成功！ " + result.message + "</span>";
        else {
            //statusEl.innerHTML = "<span style='color: red;'>❌ エラー: " + result.detail + "</span>";
        }
    } catch (err) {
        console.error(err);
        //statusEl.innerHTML = "<span style='color: red;'>❌ 登録失敗: " + err.message + "</span>";
    }
}

// --------------------------------------------------------
// 2. パスキーログイン（認証）
// --------------------------------------------------------
async function Login() {
    const username = document.getElementById("username").value;

    try {
        // 1. サーバーから認証用Optionを取得
        const resBegin = await fetch(`${BaseURL}/begin_login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const options = await resBegin.json();

        if (!resBegin.ok) {
            throw new Error(options.detail || "オプション取得失敗");
        }

        // 2. 生体認証ダイアログを起動
        const asseResp = await startAuthentication(options);

        // 3. 署名をサーバーへ送って検証
        const resComplete = await fetch(`${BaseURL}/end_login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, credential: asseResp })
        });
        const result = await resComplete.json();

        if (resComplete.ok) {
            // --- 【追加】アプリからのリダイレクト URI があるか確認 ---
            const urlParams = new URLSearchParams(window.location.search);
            const redirectUri = urlParams.get('redirect_uri');
            const token = encodeURIComponent(result)

            if (redirectUri) {
                // 安全のため localhost / 127.0.0.1 のみリダイレクトを許可
                const parsedUrl = new URL(redirectUri);
                if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
                    // Pythonアプリのローカルサーバーへトークン付きでリダイレクト
                    const separator = redirectUri.includes('?') ? '&' : '?';
                    window.location.href = `${redirectUri}${separator}token=${token}`;
                    return;
                }
            } else {
                const date = new Date();
                date.setTime(date.getTime() + (30 * 60 * 1000));
                const expires = "; expires=" + date.toUTCString();
                console.log(result);
                document.cookie = `key=${token}${expires}; path=/; SameSite=Lax`;
                //statusEl.innerHTML = "<span style='color: green;'>🎉 ログイン成功！ " + result.message + "</span>";
            }
        } else {
            //statusEl.innerHTML = "<span style='color: red;'>❌ エラー: " + result.detail + "</span>";
        }
    } catch (err) {
        console.error(err);
        //statusEl.innerHTML = "<span style='color: red;'>❌ ログイン失敗: " + err.message + "</span>";
    }
}
