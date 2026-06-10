from flask import Flask
from flask import request
import json
import oss2
from io import BytesIO,  StringIO
import pandas as pd
import numpy as np
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_eas20210701 import models as eas_20210701_models
from alibabacloud_eas20210701.client import Client as eas20210701Client
from eas_prediction import PredictClient, TFRequest
import urllib
import os
from oss2.credentials import EnvironmentVariableCredentialsProvider

app = Flask(__name__)


@app.route("/Atten_multi_predict",  methods = ['POST'])
def parameters_predict():
    
    para = request.json
    model_name = para["Atten_multi_predict"]
    file_key = para["data"]
    well_num = para["well"]
    access_key_id = "XXXXX"
    access_key_secret = "XXXXX"
    bucket_name = 'spwla-logging'
    #model_name = 'logging_test'
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, 'http://oss-cn-shanghai.aliyuncs.com', bucket_name)
    config_path="/mnt/data/pai.config"
    if os.path.isfile(config_path):
        with open(config_path) as f:
            access_key_id = f.readline().strip('\n')
            access_key_secret = f.readline().strip('\n')

    config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )

    # 访问的域名
    region = "cn-shanghai"
    config.endpoint = f'pai-eas.{region}.aliyuncs.com'
    eas_client = eas20210701Client(config)
    
    response = bucket.get_object(file_key)
    content = response.read().decode('utf-8')  # 假设文件是UTF-8编码的
    data = StringIO(content)
    df1 = pd.read_csv(data)
    # Replace -9999 with np.nan
    df1.replace(['-9999', -9999], np.nan, inplace=True)

    col_names =  ['DEN', 'GR', 'NEU', 'PEF', 'RDEP', 'RMED']
    df1 = df1.loc[(df1["WELLNUM"] == int(well_num))]
    test_data = np.array(df1.loc[:, col_names])
    test_data[:,-2:] = np.log10(test_data[:,-2:])
    
    service3 = eas_client.describe_service(cluster_id='cn-shanghai', service_name=model_name).body
    
    client = PredictClient(urllib.parse.urlsplit(service3.internet_endpoint).hostname,
                       service3.service_name)
    client.set_token(service3.access_token)
    client.init()


    test_len = test_data.shape[0]


    req = TFRequest('serving_default') # signature_name 参数:serving_default
    req.add_feed('input_1', [test_len, 6], TFRequest.DT_FLOAT, test_data.reshape((-1)))
    resp = client.predict(req)

    result_ = pd.DataFrame({'PHIF': np.array(resp.response.outputs['PHIF'].float_val),
                        'SW': np.array(resp.response.outputs['SW'].float_val), 
                        'VSH': np.array(resp.response.outputs['VSH'].float_val)})
    output_result=pd.concat([df1[['WELLNUM','DEPTH']][:], result_],axis=1)

    # 必须以二进制的方式打开文件。
    # 填写本地文件的完整路径。如果未指定本地路径，则默认从示例程序所属项目对应本地路径中上传文件。
    output_result.to_csv(f'{well_num}_parameters.csv',index=False)
    
    with open(f'{well_num}_parameters.csv', 'rb') as fileobj:
    # Seek方法用于指定从第1000个字节位置开始读写。上传时会从您指定的第1000个字节位置开始上传，直到文件结束。
        fileobj.seek(0, os.SEEK_SET)
    # Tell方法用于返回当前位置。
        current = fileobj.tell()
    # 填写Object完整路径。Object完整路径中不能包含Bucket名称。
        bucket.put_object(f'{well_num}_exampleobject.csv', fileobj)
    #bucket.put_object('output_result.csv', output_result)
    #output_result.to_csv(path_or_buf=f'./output_result.csv', index=False)
   
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


@app.route("/2DCNN_conclusion", methods=['POST'])
def parameters_predict():
    para = request.json
    model_name = para["2DCNN_conclusion"]
    file_key = para["data"]
    well_num = para["well"]
    access_key_id = "XXXXX"
    access_key_secret = "XXXXX"
    bucket_name = 'spwla-logging'
    # model_name = 'logging_test'
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, 'http://oss-cn-shanghai.aliyuncs.com', bucket_name)
    config_path = "/mnt/data/pai.config"
    if os.path.isfile(config_path):
        with open(config_path) as f:
            access_key_id = f.readline().strip('\n')
            access_key_secret = f.readline().strip('\n')

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )

    # 访问的域名
    region = "cn-shanghai"
    config.endpoint = f'pai-eas.{region}.aliyuncs.com'
    eas_client = eas20210701Client(config)

    response = bucket.get_object(file_key)
    content = response.read().decode('utf-8')  # 假设文件是UTF-8编码的
    data = StringIO(content)
    df1 = pd.read_csv(data)
    # Replace -9999 with np.nan
    df1.replace(['-9999', -9999], np.nan, inplace=True)

    col_names = ['DEN', 'GR', 'NEU', 'PEF', 'RDEP', 'RMED']
    df1 = df1.loc[(df1["WELLNUM"] == int(well_num))]
    test_data = np.array(df1.loc[:, col_names])
    test_data[:, -2:] = np.log10(test_data[:, -2:])

    service3 = eas_client.describe_service(cluster_id='cn-shanghai', service_name=model_name).body

    client = PredictClient(urllib.parse.urlsplit(service3.internet_endpoint).hostname,
                           service3.service_name)
    client.set_token(service3.access_token)
    client.init()

    test_len = test_data.shape[0]

    req = TFRequest('serving_default')  # signature_name 参数:serving_default
    req.add_feed('input_1', [test_len, 6], TFRequest.DT_FLOAT, test_data.reshape((-1)))
    resp = client.predict(req)

    result_ = pd.DataFrame({'PHIF': np.array(resp.response.outputs['PHIF'].float_val),
                            'SW': np.array(resp.response.outputs['SW'].float_val),
                            'VSH': np.array(resp.response.outputs['VSH'].float_val)})
    output_result = pd.concat([df1[['WELLNUM', 'DEPTH']][:], result_], axis=1)

    # 必须以二进制的方式打开文件。
    # 填写本地文件的完整路径。如果未指定本地路径，则默认从示例程序所属项目对应本地路径中上传文件。
    output_result.to_csv(f'{well_num}_result.csv', index=False)

    with open(f'{well_num}_result.csv', 'rb') as fileobj:
        # Seek方法用于指定从第1000个字节位置开始读写。上传时会从您指定的第1000个字节位置开始上传，直到文件结束。
        fileobj.seek(0, os.SEEK_SET)
        # Tell方法用于返回当前位置。
        current = fileobj.tell()
        # 填写Object完整路径。Object完整路径中不能包含Bucket名称。
        bucket.put_object(f'{well_num}_exampleobject.csv', fileobj)
    # bucket.put_object('output_result.csv', output_result)
    # output_result.to_csv(path_or_buf=f'./output_result.csv', index=False)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@app.route('/hello/model')
def hello_world():
    return 'Hello World'
 
    
@app.route("/",  methods = ['POST'])
def hello():
    print(request.get_json())
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)  
    
    
   