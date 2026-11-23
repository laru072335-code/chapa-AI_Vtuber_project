from comment_site import app
from quart import render_template,request 
from . import backend


@app.route('/')
async def top():
    return await render_template('top.html',pagename="top")

@app.route('/login',methods=['POST','GET'])
async def login():
    if request.method=="GET":
        return await render_template('login.html',pagename="login")
        """
        resp=await make_response(await render_template('login.html',log="ログインに成功しました",pagename="login"))
        resp.set_cookie("key",res,max_age=600,httponly=True,secure=True)
        return resp
        """
       

@app.route('/create_account',methods=['POST','GET'])
async def create_account():
    print(request.method)
    if request.method=="GET":
        print("aaa")
        return await render_template('create_account.html',pagename="create_account")
       
    
@app.route('/comments',methods=['POST','GET'])
async def comments():
    if request.method=="GET":
        return await render_template('comments.html',pagename="comments")
    if request.method=="POST":
        key=request.cookies.get("key")
        if key:
            form=await request.form
            comment=form["comment"]
            await backend.comment(comment,key)
            return await render_template('comments.html',pagename="comments",log="送信しました。")
        else:
            return await render_template('comments.html',pagename="comments",log="ログインの期限が切れたのでもう一度ログインしてください。")

@app.route('/account_setting',methods=['POST','GET'])
async def account_setting():
    if request.method=="GET":
         return await render_template('setting.html',pagename="account_setting")
    if request.method=="POST": 
        form = await request.form
        name=form["name"]
        key=request.cookies.get("key")
        if key:
            backend.setting_change(name)
        else:
            pass

     
    

    
