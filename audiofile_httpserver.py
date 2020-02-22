import os
import time
from flask import Flask,render_template,url_for,redirect,send_from_directory
# 共享文件夹的根目录
rootdir = r'/0-kaldi/egs/xvector/files/voice_register/'

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, File World!"

@app.route('/download/<subdir>/')
def document(subdir=''):
#def downloader(subdir=''):
    print("test:if subdir == '':")
    if subdir == '':
        # 名字为空，切换到根目录
        os.chdir(rootdir)
    else:
        fullname = rootdir + os.sep + subdir
        print('fullname:',fullname)
        #  如果是文件，则下载
        if os.path.isfile(fullname):
 #           return redirect(url_for('download', fullname=fullname))
            return send_from_directory(rootdir, subdir, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7878, debug=True,ssl_context=('/data/ssl/ssl.crt','/data/ssl/ssl.key'))
