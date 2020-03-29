import os
from flask import Flask,send_from_directory,request
# 共享文件夹的根目录
rootdir = r'/0-kaldi/egs/xvector/denoise_files/'

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, File World!"


@app.route('/download/', methods = ["GET","POST"])
def document():
# http://10.8.54.48:5000/index?url=john&age=20
    file_url = request.args.get("url")
    print("file_url:",file_url)
    fullname = rootdir + os.sep + file_url
    print('fullname:',fullname)
    #  如果是文件，则下载
    if os.path.isfile(fullname):
        return send_from_directory(rootdir, file_url, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7979, debug=True,ssl_context=('/data/ssl/ssl.crt','/data/ssl/ssl.key'))
