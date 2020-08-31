from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import time
from urllib.request import urlopen
#The API below helps in fetching data
from imdb import IMDb
import threading
import requests
from random import seed,random,randint
import re
import sys
#The array in which the information of movies will get appended
data = []

## PROXIES
#proxy = {"https": "185.56.209.114:51386"}
s = requests.Session()
#Incase a particular proxy gets blocked then just a different proxy needs to be added here.
s.proxies = {"http": "http://50.203.239.18:80"}
seed(1)
#The value in BoundedSemaphore decides the number of threads(windows) which can simultaneously run.
#The greater the number of threads, greater the speed but then you run the risk of being an aggressive crawler and will get banned accordingly.
lock = threading.BoundedSemaphore(25)

## GENERATING THE LISTS OF MOVIES
set_mov = {'None'}
movie_names=[]
wiki_url = "https://en.wikipedia.org/wiki/List_of_American_films_of_{0}"
#The range of for loop is from which year we want to feth movies.
for i in range(1990,2020):
    content = s.get(wiki_url.format(i)).text
    soup = BeautifulSoup(content,'lxml')
    #Obtain the table which contains the names of the movies released in a particular year
    tables = soup.find_all('table',class_='wikitable')
    for item in tables:
        rows = item.find_all('i')
        for val in rows:
            try:
                text=val.string
                if(text!=None):
                    movie_names.append(text)
            except:
                movie_names.append('Error occured')
#We remove the duplicate names.
movie_names = list(dict.fromkeys(movie_names))
print(len(movie_names))

#The driver code is written below the movie_page function

#The important function
def movie_page(num1, num2, movie_names):
    #Create an imdb object using the API
    imdb_obj = IMDb()
    for i in range(num1, num2, 1):
        flag_movie_url = 1
        r_val = 0
        time_val = 0
        votes_val = 0
        metascore = 0
        moviename=movie_names[i]
        prod_house=None
        usa_revenue = None
        world_revenue = None
        budget = None
        metacritic_critic=None
        metacritic_user=None
        director = None
        writer = None
        actors=""
        genres=""
        try:
            #Attempt to acquire the lock which would allow the thread to fetch the data or else keeps the tread in wait stage
            lock.acquire()
            # This sleep call is used to prevent bombarding the Imdb server with a lot of calls to its website.
            # Be careful that at times the sleep intervals need to be of higher values so that frequency of the requests can be deemed permissible by Imdb servers.
            time.sleep(randint(6, 9))
            #Using the Imdb API to fetch relevant data of movie url and using that to obtain the movie_object
            rating_url = imdb_obj.get_imdbURL(imdb_obj.search_movie(movie_names[i])[0])
            movie_object = imdb_obj.get_movie(imdb_obj.search_movie(movie_names[i])[0].movieID)
        except:
            flag_movie_url = 0
            lock.release()
            print('Failed to get movie URL.')
        if (flag_movie_url == 1):
            #The step below is necessary as typical execution fails to store the characters of names of people who are spanish, french, etc.
            content = s.get(rating_url).content
            soup = BeautifulSoup(content.decode('utf-8','ignore'),'lxml')
            try:
                #This fetches the Imdb rating.
                rating_value = soup.find('div', class_='ratingValue').find('span')
                r_val = float(rating_value.string)
            except:
                r_val = None
            #Find the number of metacritic critics and users who rated the movie using BS4 and RegEx
            try:
                metacritic_ratingdivs = soup.find('div', class_="titleReviewBarItem titleReviewbarItemBorder").find_all('a')
                metacritic_ratingdiv_count=0;
                for meta_div in metacritic_ratingdivs:
                    if(metacritic_ratingdiv_count==0):
                        metacritic_critic = int(re.findall(r"\d{5}|\d{4}|\d{3}|\d{2}|\d{1}", meta_div.string.replace(',', ''))[0])
                    if(metacritic_ratingdiv_count==1):
                        metacritic_user = int(re.findall(r"\d{5}|\d{4}|\d{3}|\d{2}|\d{1}", meta_div.string.replace(',', ''))[0])
                    metacritic_ratingdiv_count+=1
            except:
                pass
            # Find duration of movie using the API
            try:
                time_val = int(movie_object['runtimes'][0])
            except:
                time_val = None
            #Find the director, writer, star actors of the movie using BS4
            try:
                divs = soup.find_all('div', class_="credit_summary_item")
                count = 0
                for div in divs:
                    if (count == 0):
                        try:
                            director = div.find('a').string
                        except:
                            pass
                    if (count == 1):
                        try:
                            writer = div.find('a').string
                        except:
                            pass
                    if (count == 2):
                        try:
                            list_of_a_tags = div.find_all('a')
                            for a in list_of_a_tags:
                                if (a.string == "See full cast & crew"):
                                    break
                                actors += a.string + ","
                        except:
                            pass
                    count += 1
                try:
                    actors = actors[0:len(actors) - 1]
                except:
                    actors=None
            except:
                actors=None
            #Find the genres of the movie using BS4
            try:
                genrediv = soup.find('div', class_='subtext')
                list_of_a_tags = genrediv.find_all('a')
                for a in list_of_a_tags:
                    if (re.findall(r"\d{4}", a.string)):
                        break
                    genres += a.string + ','
                try:
                    genres = genres[0:len(genres) - 1]
                except:
                    genres=None
            except:
                genres=None
            # Find the votes of movie using BS4
            try:
                votes_val = int(soup.find('span',class_='small').string.replace(',',''))
            except:
                votes_val = None
            # Find the metascore of the movie using BS4
            try:
                metascore = float(soup.find('div', class_="titleReviewBarItem").find('span').string)
            except:
                metascore = None
            # Find the budget, Production House, revenue of movie in USA and over the world using BS4 and RegEx
            try:
                divs = soup.find('div', id='titleDetails').find_all('div', class_='txt-block')
                h4_count = 0
                for div in divs:
                    if (h4_count> 12):
                        break
                    if (div.find('h4', class_='inline').string == "Budget:"):
                        budget_array = re.findall('\d{3}|\d{2}|\d{1}', div.text)
                        budget = ''
                        for i in budget_array:
                            budget += i
                    if (div.find('h4', class_='inline').string == "Gross USA:"):
                        usa_revenue_array = re.findall('\d{3}|\d{2}|\d{1}', div.text)
                        usa_revenue = ''
                        for i in usa_revenue_array:
                            usa_revenue += i
                    if (div.find('h4', class_='inline').string == "Cumulative Worldwide Gross:"):
                        world_revenue_array = re.findall('\d{3}|\d{2}|\d{1}', div.text)
                        world_revenue = ''
                        for i in world_revenue_array:
                            world_revenue += i
                    if (div.find('h4', class_='inline').string == "Production Co:"):
                        prod_house = div.find('a').string.strip()
                    h4_count += 1
            except:
                pass
            # Find the year in which movie was released using BS4
            try:
                year = int(soup.find('div', class_='title_wrapper').find('span', id='titleYear').find('a').text)
            except:
                year = None
            #We add the information using append method which is thread safe.
            data.append([year, moviename, time_val,director,writer,actors,genres,prod_house, budget, usa_revenue, world_revenue, votes_val, r_val,metacritic_critic,metacritic_user, metascore])
            #So that a waiting thread can execute
            lock.release()
            print(len(data))

thread_array = []
#Used to allocate the number of movies to each thread. The value of denominator can be adjusted as needed.
step = round(len(movie_names) / 50, ndigits=None)
for i in range(0, len(movie_names), step):
    if (i != 0):
        i += 1
    if (i + step < len(movie_names)):
        t = threading.Thread(target=movie_page, args=(i, i + step, movie_names,))
    else:
        t = threading.Thread(target=movie_page, args=(i, i + len(movie_names) % step - 1, movie_names,))
    thread_array.append(t)
for i in thread_array:
    i.start()
for i in thread_array:
    i.join()

df = pd.DataFrame(data=data, columns=['Year Released','Movie Name','Runtime (Minutes)','Director','Writer','Cast','Genres','Production House','Budget','USA Revenue','Worldwide Revenue','IMDB Votes','IMDB Rating','Metacritic Critics','Metacritic Users','Metascore'])
print(df.info())
df.to_csv(r"1990_2019_movies.csv")
