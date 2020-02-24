#!coding=utf-8
import hashlib,flask
import os, json, random, time
from ffmpy import FFmpeg
from flask import Flask  # , request, jsonify
from flask_cors import *
from datetime import datetime
import pandas as pd
from shutil import copyfile
import numpy as np
import requests
#import sqlitedb


app = Flask(__name__)
CORS(app, supports_credentials=True)


@app.route('/')
def index():
    return "Hello, World!"


app.config['UPLOAD_FOLDER'] = 'files/voice_register'
app.config['recognition_folder'] = 'files/voice_recognition'
app.config['ALLOWED_EXTENSIONS'] = ['wav','WAV','MP3','mp3','M4A','m4a']
os.popen("export LANG='zh_CN.uft8'")

# 返回向量角度结果组
def get_angle(vector_mat, vector_arr):
    vector_mat_norm = np.linalg.norm(vector_mat,axis=1)
    vector_arr_norm = np.linalg.norm(vector_arr)

    mat_dot_arr = vector_mat.dot(vector_arr)
    cos_value = mat_dot_arr / (vector_mat_norm * vector_arr_norm)
    # 保留6位小数点的精度，以防出现cos值超过[-1,1]的范围
    cos_value=cos_value.map(lambda x:float("%.6f" % x))
    # 返回经过带有索引的排序的角度结果组（索引为MD5值）
    angle_ser=cos_value.map(lambda x: np.rad2deg(np.arccos(x))).sort_values()
    return angle_ser

# 获取音频文件md5值
def get_md5(filename):
    m = hashlib.md5()
    mfile = open(filename, 'rb')
    m.update(mfile.read())
    mfile.close()
    md5value = m.hexdigest()
    return md5value

# 向文件追加写入数据
def write_file(filename, lines):
    with open(filename, 'at') as f:
        f.writelines(lines)

# 音频文件格式转换为WAV
def format_converter(intput_file,output_file):
    #os.system('ffmpeg -y -i %s -f wav %s' %(intput_file,output_file))
    ff = FFmpeg(
        inputs={intput_file: '-y'},
        outputs={output_file: '-f wav'}
    )
    ff.run()
    print('output_file:',output_file)
    return output_file

# 获取音频文件向量及MD5值
def ext_xvector(audio_file,save_dir,train_dir):
    # 获取文件名及后缀
    #filename, filetype = audio_file.filename.split('.')
    filename, filetype = os.path.splitext(audio_file.filename)
    # 去掉后缀名中的.
    filetype=filetype.replace('.','')
    print(filename,filetype)
    if filetype in ['wav', 'WAV']:
        # 如果后缀为wav文件直接保存音频文件
        save_file_path = os.path.join(app.root_path, save_dir, audio_file.filename)
        audio_file.save(save_file_path)
    elif filetype in ['MP3', 'mp3', 'm4a', 'M4A']:
        # 首先保存音频文件
        file_path = os.path.join(app.root_path, 'files/init_voice', audio_file.filename)
        audio_file.save(file_path)
        # 转换为wav格式
        output_filepath = os.path.join(app.root_path, save_dir, filename + '.wav')
        save_file_path = format_converter(file_path, output_filepath)
    # 计算MD5
    md5=get_md5(save_file_path)
    file_name_md5 = md5 + '.wav'
    # MD5值重命名音频文件
    new_file_path = os.path.join(app.root_path, save_dir, file_name_md5)
    os.rename(save_file_path, new_file_path)

    # 音频文件拷贝到训练文件夹
    train_wav_target = os.path.join(app.root_path, train_dir, file_name_md5)
    copyfile(new_file_path, train_wav_target)

    # 抽取xvector
    try:
        os.system('./enroll.sh %s 1' % train_dir)
        os.system('./ext_xvector.sh')
        # 删除已抽取向量的文件
        os.remove(train_wav_target)
        # 读取向量到列表
        with open('xvectorall.txt', 'r') as file:
            data = file.readlines()
            vector_list = []
            for row in data:
                rowdata = row.strip().replace('[', '').replace(']', '').split('  ')
                label = rowdata[0]
                # vector=np.array(rowdata[1].strip().split(), dtype=float)
                vector = rowdata[1].strip()
                vector_list.append(label + ' ')
                vector_list.append(vector + '\n')
    except Exception as e:
        print(e)
    # 返回向量列表
    return vector_list,md5

# 通过微信服务器获取openid
def get_openid(jscode):
    try:
        url = "https://api.weixin.qq.com/sns/jscode2session"
        appid = 'wxbcacb6dcd28daebd'
        secret = 'd5681f69cc19462001193bfa82516397'
        jscode=jscode
        newurl = url + "?appid=" + appid + "&secret=" + secret + "&js_code=" + jscode + "&grant_type=authorization_code"
        r = requests.get(newurl)
        res_dic={}
        if 'openid' in r.json().keys():
            openid = r.json()['openid']
            res_dic['data']=openid
            res_dic['code']=1
        elif 'errmsg' in r.json().keys():
            errmsg = r.json()['errmsg']
            res_dic['data']=errmsg
            res_dic['code']=0
    except Exception as e:
        res_dic['data'] = str(e)
        res_dic['code'] = 0
    return res_dic

def if_openid_exist(openid):
    # 第1列为id列
    data = pd.read_table('info_db.txt', header=None, sep='|')
    res_dic={}
    if openid in data.iloc[:, 0].values:
        res_dic['data'] = 'This ID existed.'
        res_dic['code'] = 1
    else:
        res_dic['data'] = openid
        res_dic['code'] = 0
    return res_dic

@app.route("/if_id_exist", methods=["POST"])
def if_id_exist():
    res_dic = {}
    if flask.request.method == "POST":
        try:
            if flask.request.form.get("openid"):
                openid=flask.request.form.get("openid")
                print('openid:',openid)
                res_dic=if_openid_exist(openid)
                # return json.dumps(res_dic)
            elif flask.request.form.get("jscode"):
                jscode=flask.request.form.get("jscode")
                print('JSCODE:',jscode)
                # 获取openid
                res=get_openid(jscode)
                print('openid:',res)
                # 如果获取openid成功
                if res['code']==1:
                    # 如果id存在
                    openid=res['data']
                    res_dic=if_openid_exist(openid)
                # 如果获取openid不成功
                elif res['code'] == 0:
                    # 返回错误信息
                    res_dic['data'] = res['data']
                    res_dic['code'] = 2
            else:
                print('Parameters are not right, did not receive the openid or jscode')
                res_dic['data'] = 'Parameters are not right, did not receive the openid or jscode'
                res_dic['code'] = 2
        except Exception as e:
            res_dic['data']=str(e)
            res_dic['code']=2
    else:
        res_dic['data'] = 'The method must be POST'
        res_dic['code'] = 2
    print(res_dic)
    return json.dumps(res_dic)

@app.route("/if_id_exist_from_jscode", methods=["POST"])
def if_id_exist_from_jscode():
    res_dic = {}
    if flask.request.method == "POST":
        if flask.request.form.get("jscode"):
            try:
                jscode=flask.request.form.get("jscode")
                print('JSCODE:',jscode)
                # 获取openid
                res=get_openid(jscode)
                print('openid:',res)
                # 如果获取openid成功
                if res['code']==1:
                    # 如果id存在
                    openid=res['data']
                    res_dic=if_openid_exist(openid)
                    # if openid in data.iloc[:,0].values:
                    #     res_dic['data'] = 'This ID existed.'
                    #     res_dic['code'] = 1
                    # else:
                    #     res_dic['data'] = openid
                    #     res_dic['code'] = 0
                # 如果获取openid不成功
                elif res['code'] == 0:
                    # 返回错误信息
                    res_dic['data'] = res['data']
                    res_dic['code'] = 2
            except Exception as e:
                res_dic['data']=str(e)
                res_dic['code']=2
            # return json.dumps(res_dic)
        else:
            print('Parameters are not right, did not receive the jscode')
            res_dic['data'] = 'Parameters are not right, did not receive the id'
            res_dic['code'] = 2
            # return json.dumps(res_dic)
    else:
        res_dic['data'] = 'The method must be POST'
        res_dic['code'] = 2
    print(res_dic)
    return json.dumps(res_dic)

@app.route("/gather", methods=["POST"])
def gather():
    res_dic = {}
    if flask.request.method == "POST":
        # if flask.request.files.get("audio") and flask.request.form.get("channel"):
        if flask.request.files.get("audio") and flask.request.form.get("info"):
            try:
                # 获取上传文件
                audio_file = flask.request.files["audio"]
                print(audio_file,type(audio_file))
                print(flask.request.form.get("info"))
                print(type(flask.request.form.get("info")))
                # 获取上传信息并转为dict
                info=json.loads(flask.request.form.get("info"))
                # print(audio_file)
                #init_file_name=audio_file.filename
                # 把向量保存到向量库表
                vector_list,md5=ext_xvector(audio_file,app.config['UPLOAD_FOLDER'],'wav_applet/register_train')
                write_file('xvector_db.txt',vector_list)
                # 将微信信息保存到信息表
                code=if_openid_exist(info['id'])['code']
                #如果openid不在表里则保存信息
                if code==0:
                    info_list=[]
                    info_list.append(info['id'] + '|')
                    info_list.append(info['nickname'] + '|')
                    info_list.append(str(info['sex']) + '\n')
                    write_file('info_db.txt', info_list)
                #sqlitedb.insert_wx_info(info['id'], info['nickname'], info['sex'])
                # 把语音文件信息保存到文件列表
                audiofile_list=[]
                file_idr=os.path.join('..', app.config['UPLOAD_FOLDER'], md5+'.wav')
                audiofile_list.append(info['id'] + ' ')
                audiofile_list.append(md5 + ' ')
                audiofile_list.append(file_idr + '\n')
                write_file('audiofile_db.txt', audiofile_list)
                # 返回结果
                res_dic['data']='Gather succeeded.'
                res_dic['code']=1
            except Exception as e:
                res_dic['data']=str(e)
                res_dic['code']=0
        else:
            print('Parameters are not right, did not receive the audio file or info!')
            res_dic['data'] = 'Parameters are not right, did not receive the audio file or info!'
            res_dic['code'] = 0
    else:
        res_dic['data'] = 'The method must be POST'
        res_dic['code'] = 0
    return json.dumps(res_dic)


@app.route("/recognition", methods=["POST"])
def recognition():
    res_dic = {}
    if flask.request.method == "POST":
        # if flask.request.files.get("audio") and flask.request.form.get("channel"):
        if flask.request.files.get("audio"):
            try:
                # 获取上传的待识别语音文件
                audio_file = flask.request.files["audio"]
                filename,filetype = audio_file.filename.split('.')
                # 如果后缀符合条件
                if filetype in app.config['ALLOWED_EXTENSIONS']:
                    # 获取待识别音频文件向量列表
                    vector_list,md5 =ext_xvector(audio_file, app.config['recognition_folder'], 'wav_applet/recognition_train')
                    xvector_rec=np.array(vector_list[1].strip().split(' '),dtype=float)
                    # 读取全体注册向量表
                    xvector_db = pd.read_table(r'xvector_db.txt', header=None, sep=' ',index_col=0)
                    # 返回待识别音频文件向量与全体注册向量的匹配结果（角度矩阵）
                    angle_mat=pd.DataFrame(get_angle(xvector_db,xvector_rec))
                    # 读取信息表
                    info_db = pd.read_table(r'info_db.txt', header=None, sep='|',index_col=0)
                    info_db.columns=['nickname','sex']
                    # 读取音频文件列表
                    audiofile_db = pd.read_table(r'audiofile_db.txt', header=None, sep=' ',index_col=1)
                    audiofile_db.columns=['wechat_id','file_url']
                    # file_url替换成下载连接
                    audiofile_db['file_url'] = audiofile_db['file_url'].map(
                        lambda x: x.replace('../files/voice_register', 'https://banana-b08n2oze.pai.tcloudbase.com:7878/download'))
                        #lambda x: x.replace('..', 'http://192.168.1.232:7878'))
                    # 返回包含人员信息、文件信息和匹配角度的整体结果
                    result=angle_mat.join(audiofile_db).merge(info_db,left_on='wechat_id',right_on=info_db.index)
                    result.rename(columns={0:'score'}, inplace=True)
                    # 以分数排序 
                    result.sort_values(by = 'score',axis = 0,ascending = True,inplace=True)
                    # 返回前30
                    result=result.iloc[:30,:]
                    # 以行方向转为字典格式
                    result_dict=json.loads(result.to_json(orient='index'))
                    # 每行插入到列表
                    res_list=[]
                    for key in result_dict:
                        res_list.append(result_dict[key])
                    print(res_list)
                    #res_json=json.dumps(result.to_dict(orient='list'))

                    res_dic['data'] = res_list
                    res_dic['code'] = 1
                # 如果后缀不符合条件，返回提示
                else:
                  return json.dumps({'data':'Unsupported media types. Must be wav mp3 or m4a!','code':0})
            except  Exception as e:
                res_dic['data']=str(e)
                res_dic['code']=0
        else:
            res_dic['data'] = 'Parameters are not right, did not receive the audio parameter'
            res_dic['code'] = 0
    else:
        res_dic['data'] = 'The method must be POST'
        res_dic['code'] = 0
    #print(res_dic)
    return json.dumps(res_dic)

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=3000, debug=True)
    #app.run(host='0.0.0.0', port=3000, debug=True,ssl_context='adhoc')
    app.run(host='0.0.0.0', port=6006, debug=True,ssl_context=('/data/ssl/ssl.crt','/data/ssl/ssl.key'))
    #app.run(host='192.168.1.232', port=6006, debug=True)


