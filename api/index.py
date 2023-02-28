from flask import Flask, render_template , request , jsonify
from pytube import YouTube,Search
# from kofisearch.app import KofiSearch
import logging
logger = logging.getLogger(__name__)
app = Flask(__name__)
class KofiSearch(Search):
    def __init__(self, query):
        super().__init__(query)
    def fetch_and_parse(self, continuation=None):
        """Fetch from the innertube API and parse the results.

        :param str continuation:
            Continuation string for fetching results.
        :rtype: tuple
        :returns:
            A tuple of a list of YouTube objects and a continuation string.
        """
        # Begin by executing the query and identifying the relevant sections
        #  of the results
        raw_results = self.fetch_query(continuation)

        # Initial result is handled by try block, continuations by except block
        try:
            sections = raw_results['contents']['twoColumnSearchResultsRenderer'][
                'primaryContents']['sectionListRenderer']['contents']
        except KeyError:
            sections = raw_results['onResponseReceivedCommands'][0][
                'appendContinuationItemsAction']['continuationItems']
        item_renderer = None
        continuation_renderer = None
        for s in sections:
            if 'itemSectionRenderer' in s:
                item_renderer = s['itemSectionRenderer']
            if 'continuationItemRenderer' in s:
                continuation_renderer = s['continuationItemRenderer']

        # If the continuationItemRenderer doesn't exist, assume no further results
        if continuation_renderer:
            next_continuation = continuation_renderer['continuationEndpoint'][
                'continuationCommand']['token']
        else:
            next_continuation = None

        # If the itemSectionRenderer doesn't exist, assume no results.
        if item_renderer:
            videos = []
            raw_video_list = item_renderer['contents']
            for video_details in raw_video_list:
                # Skip over ads
                if video_details.get('searchPyvRenderer', {}).get('ads', None):
                    continue

                # Skip "recommended" type videos e.g. "people also watched" and "popular X"
                #  that break up the search results
                if 'shelfRenderer' in video_details:
                    continue

                # Skip auto-generated "mix" playlist results
                if 'radioRenderer' in video_details:
                    continue

                # Skip playlist results
                if 'playlistRenderer' in video_details:
                    continue

                # Skip channel results
                if 'channelRenderer' in video_details:
                    continue

                # Skip 'people also searched for' results
                if 'horizontalCardListRenderer' in video_details:
                    continue

                # Can't seem to reproduce, probably related to typo fix suggestions
                if 'didYouMeanRenderer' in video_details:
                    continue

                # Seems to be the renderer used for the image shown on a no results page
                if 'backgroundPromoRenderer' in video_details:
                    continue

                if 'videoRenderer' not in video_details:
                    logger.warn('Unexpected renderer encountered.')
                    logger.warn(f'Renderer name: {video_details.keys()}')
                    logger.warn(f'Search term: {self.query}')
                    logger.warn(
                        'Please open an issue at '
                        'https://github.com/pytube/pytube/issues '
                        'and provide this log output.'
                    )
                    continue

                # Extract relevant video information from the details.
                # Some of this can be used to pre-populate attributes of the
                #  YouTube object.
                vid_renderer = video_details['videoRenderer']
                vid_id = vid_renderer['videoId']
                vid_url = f'https://www.youtube.com/watch?v={vid_id}'
                vid_title = vid_renderer['title']['runs'][0]['text']
                vid_channel_name = vid_renderer['ownerText']['runs'][0]['text']
                vid_channel_uri = vid_renderer['ownerText']['runs'][0][
                    'navigationEndpoint']['commandMetadata']['webCommandMetadata']['url']
                # Livestreams have "runs", non-livestreams have "simpleText",
                #  and scheduled releases do not have 'viewCountText'
                if 'viewCountText' in vid_renderer:
                    if 'runs' in vid_renderer['viewCountText']:
                        vid_view_count_text = vid_renderer['viewCountText']['runs'][0]['text']
                    else:
                        vid_view_count_text = vid_renderer['viewCountText']['simpleText']
                    # Strip ' views' text, then remove commas
                    stripped_text = vid_view_count_text.split()[0].replace(',','')
                    if stripped_text == 'No':
                        vid_view_count = 0
                    else:
                        vid_view_count = int(stripped_text)
                else:
                    vid_view_count = 0
                if 'lengthText' in vid_renderer:
                    vid_length = vid_renderer['lengthText']['simpleText']
                else:
                    vid_length = None

                vid_metadata = {
                    'id': vid_id,
                    'url': vid_url,
                    'title': vid_title,
                    'channel_name': vid_channel_name,
                    'channel_url': vid_channel_uri,
                    'view_count': vid_view_count,
                    'length': vid_length
                }

                # Construct YouTube object from metadata and append to results
                vid = YouTube(vid_metadata['url'])
                vid.watch_url = vid_url;
                vid.author = vid_metadata['channel_name']
                vid.title = vid_metadata['title']
                videos.append(vid)
        else:
            videos = None

        return videos, next_continuation


def getFromYoutube(query):
    searchresults=KofiSearch(query);
    
@app.route('/')
def home():
    return """
    <span>/ytsuggest?keyword=</span>
    <span>/query/audio/?yturl=</span>
    <span>/query/video/?yturl=</span>
    <span>/search/songs?keyword=</span>
    """
@app.route('/ytsuggest')
def ytsuggest():
    keyword=request.args.get('keyword', default = 1, type = str)
    query=KofiSearch(keyword)
    return jsonify({'suggested':query.completion_suggestions})

@app.route('/query/audio')
def querySearch():
    url=request.args.get('yturl')
    yt=YouTube(url)
    streams=yt.streams;
    aud={'title':""+streams.filter(only_audio=True).first().title,'downloadlinks':{},'thumbnail':yt.thumbnail_url}
    # streams.filter(only_audio=True).first()
    for audioObj in streams.filter(only_audio=True):
        aud['downloadlinks'][''+str(audioObj.abr)]=audioObj.url
    return jsonify({'respose':aud})

@app.route('/search/songs')
def searchsong():
    keyword=request.args.get('keyword', default = 1)
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

@app.route('/query/video')
def searchvideo():
    url=request.args.get('yturl')
    yt=YouTube(url)
    streams=yt.streams;
    aud={'title':""+streams.filter(only_audio=True).first().title,'downloadlinks':{},'thumbnail':yt.thumbnail_url}
    #streams.filter(progressive=False).first().video_codec
    for audioObj in streams.filter():
        aud['downloadlinks'][''+str(audioObj.res)]=audioObj.url
    return jsonify({'respose':aud})


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
