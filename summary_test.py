from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from typing import Optional, List, Dict
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import time
import datetime
import locale
from slack_sdk import WebClient

load_dotenv()
chat_model = ChatOpenAI(model_name="gpt-3.5-turbo")


def fetch_webpage(url: str) -> Optional[bytes]:
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        return None


def parse_content(html_content: bytes) -> List[str]:
    soup = BeautifulSoup(html_content, 'html.parser')
    base_selector = "#container > section > div > section > div.sec_body > div > ul > li:nth-child({}) > a"
    hrefs = []
    for i in range(1, 11):
        selector = base_selector.format(i)
        a_tag = soup.select_one(selector)
        if a_tag:
            hrefs.append(a_tag['href'])
    return hrefs


def summarize_ai(to_summarize: str) -> str:
    result = chat_model.predict(f"""
                            이제부터 너는 기사를 요약해주는 봇이야. 대답할 필요없이
                            아래의 기사를 읽고, 200자 이내로 요약을 부탁할게.
                            {to_summarize}
                            형식은 다음과 같아!
                            요약부분(200자이내)
                            """)
    return result


def fetch_article_details(url_list: list) -> dict:
    title, datetime, content, summary = [], [], [], []
    for url in url_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        if soup.find('div', class_='locked_wrapper'):
            continue
        individual_title = soup.find(
            'h2', class_="news_ttl").get_text().strip()
        individual_datetime = soup.find(
            'dl', class_='registration').find('dd').get_text().strip()
        individual_content = soup.find('div', class_='news_cnt_detail_wrap')
        individual_content_list = [i.get_text().replace('“', '').replace(
            '”', '').replace('  ', '').replace('\n', '') for i in individual_content]
        individual_contents = ' '.join(individual_content_list)
        indivdual_summary = summarize_ai(individual_contents)
        title.append(individual_title)
        datetime.append(individual_datetime)
        content.append(individual_contents)
        summary.append(indivdual_summary)
        time.sleep(0.5)
    return {'title': title, 'datetime': datetime, 'content': content, 'summary': summary, 'url': url_list}


def format_message(date: str, data: dict) -> str:
    locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
    formatted_data = f"🤖AI가 요약한 {date} 뉴우-스\n\n"
    for i in range(len(data['title'])):
        formatted_data += f"{i+1}. {data['title'][i]}\n{data['summary'][i]}\nurl:[{data['url'][i]}]\n\n"
    return formatted_data


def message_to_channel(slack_token: str, channel: str, text: str):
    client = WebClient(token=slack_token)
    client.chat_postMessage(channel=channel, text=text)


url = 'https://www.mk.co.kr/news/ranking/economy/'
html_content = fetch_webpage(url)
if html_content:
    url_list = parse_content(html_content)
    daily_economy_news = fetch_article_details(url_list)
    now = datetime.datetime.now()
    formatted_date = now.strftime("%Y년 %m월 %d일 %A")
    formatted_msg = format_message(formatted_date, daily_economy_news)
    slack_token = "xoxb-5957647747094-5964252974531-gUxrYMbOFVZO16kF0TA1twRn"  # 실제 토큰으로 교체하세요
    message_to_channel(slack_token, "#매일경제-인기뉴스", formatted_msg)
else:
    print("Failed to retrieve the webpage.")
