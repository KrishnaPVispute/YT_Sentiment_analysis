import re
from flask import Flask, render_template, request
from googleapiclient.discovery import build
from textblob import TextBlob
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)

API_KEY = '12314332545AIzaSyB8J1XWGQ3avd5jSkbx9mJcsEoV2rK7E88,dfdfdfdfsadg'  
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def extract_video_id(youtube_url):
    match = re.match(r'(https?://(?:www\.)?youtube\.com/watch\?v=|https?://youtu\.be/)([A-Za-z0-9_-]{11})', youtube_url)
    if match:
        return match.group(2)
    else:
        raise ValueError("Invalid YouTube URL or video ID could not be extracted.")


def get_video_comments(youtube, video_id):
    comments = []
    response = youtube.commentThreads().list(
        part='snippet',
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    ).execute()

    while response:
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
        
        if 'nextPageToken' in response:
            response = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                pageToken=response['nextPageToken'],
                maxResults=100,
                textFormat="plainText"
            ).execute()
        else:
            break
    return comments


def clean_comment(text):
    text = re.sub(r"http\S+|www\S+|https\S+", '', text, flags=re.MULTILINE)
    text = re.sub(r'\@\w+|\#', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text


def analyze_sentiment(comments):
    sentiment_results = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    for comment in comments:
        analysis = TextBlob(clean_comment(comment))
        polarity = analysis.sentiment.polarity
        if polarity > 0:
            sentiment_results['Positive'] += 1
        elif polarity < 0:
            sentiment_results['Negative'] += 1
        else:
            sentiment_results['Neutral'] += 1
    return sentiment_results


def calculate_percentage(sentiment_counts, total_comments):
    return {k: (v / total_comments) * 100 for k, v in sentiment_counts.items()}


def plot_sentiment(percentages):
    labels = percentages.keys()
    sizes = percentages.values()
    colors = ['#4CAF50', '#F44336', '#FFEB3B']
    explode = (0.1, 0.1, 0.1)
    
    
    plt.figure(figsize=(10, 10))
    
    plt.pie(
        sizes,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        shadow=True,
        startangle=140,
        textprops={'fontsize': 14}  
    )
    plt.axis('equal')  

    
    img_io = BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight')
    img_io.seek(0)

    
    img_b64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

    
    plt.clf()

    return img_b64


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    youtube_url = request.form['youtube_url']
    try:
        video_id = extract_video_id(youtube_url)
        youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)
        comments = get_video_comments(youtube, video_id)
        
        if not comments:
            return "No comments found."

        sentiment_counts = analyze_sentiment(comments)
        total_comments = len(comments)
        percentages = calculate_percentage(sentiment_counts, total_comments)
        
        # Generate sentiment plot
        img_b64 = plot_sentiment(percentages)

        # Return the result page with sentiment data and pie chart image
        return render_template('result.html', percentages=percentages, img_b64=img_b64)

    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    app.run(debug=True)
