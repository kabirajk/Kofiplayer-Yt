from flask import Flask, render_template , request , jsonify
from pytube import YouTube,Search
from api.app import KofiSearch
import logging
logger = logging.getLogger(__name__)
app = Flask(__name__)
    
def getFromYoutube(query):
    searchresults=KofiSearch(query);
    
@app.route('/')
def home():
    return 'Hello, World!'
@app.route('/ytsuggest')
def ytsuggest():
    keyword=request.args.get('keyword', default = 1, type = str)
    query=KofiSearch(keyword)
    return jsonify({'suggested':query.completion_suggestions})

@app.route('/query')
def querySearch():
    keyword=request.args.get('keyword', default = 1, type = str)
    
    return 'Hello, World!'

@app.route('/search/songs')
def searchsong():
    keyword=request.args.get('keyword', default = 1, type = str)
    query=KofiSearch(keyword)
    responseDict={'response':[]};
    queryl=dict()
    for YtVidObj in query.results:
        queryl[YtVidObj.title] = YtVidObj.watch_url
    
    for key in queryl:
        yt=YouTube(queryl[key])
        streams=yt.streams;
        aud={'title':""+streams.filter(only_audio=True).first().title,'downloadlinks':{}}
        streams.filter(only_audio=True).first()
        for audioObj in streams.filter(only_audio=True):
            aud['downloadlinks'][''+str(audioObj.bitrate)]=audioObj.url
        responseDict['response'].append(aud)
    return jsonify({'responses':responseDict})

@app.route('/search/video')
def searchvideo():
    return 'Hello, World!'


@app.route('/test' , methods=['GET'])
def test():
	# print("log: got at test" , file=sys.stderr)
	return jsonify({'status':'succces'})

@app.after_request
def after_request(response):
    # print("log: setting cors" ,os.curdir, file = sys.stderr)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


@app.route('/about')
def about():
    return 'About'

# app.run(debug=True)