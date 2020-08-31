#We will import the creating_model file.
import creating_model
import pickle
import requests
from imdb import IMDb
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
#Import the saved model, dataset and the name of columns. Dont get confused between the import and the dataset, the former is used only in one line
lm,IMDB,feature_columns=creating_model.create_model()
#Creating the object using proxy for accessing some information
imdb_obj = IMDb()
s = requests.Session()
s.proxies = {"http": "http://50.203.239.28:80"}

def predict_rating(movie_name,year_released):
    movie_name = movie_name# + ' (' + str(year_released) + ')'
    # Load the data of the new movie whose rating is to be found. The name is written in format of "name (year)"
    link = imdb_obj.get_imdbURL(imdb_obj.search_movie(movie_name)[0])
    movie_object = imdb_obj.get_movie(imdb_obj.search_movie(movie_name)[0].movieID)
    content = s.get(link).content
    print(link)
    soup = BeautifulSoup(content.decode('utf-8', 'ignore'), 'lxml')
    # Need to find the name of director, writer, cast and the genres of the movie as well as
    # its runtime, production house and description.
    director = None
    writer = None
    cast = []
    genres = []
    runtime = None
    pred_runtime = None
    production_house = None
    movie_desc = None
    actors = ""
    genre_string = ""
    imdb_rating = None
    metascore = None

    # Find duration of movie.
    try:
        runtime = int(movie_object['runtimes'][0])
        pred_runtime = runtime
    except:
        pred_runtime = None
    # Finding actual IMDB Rating if available.
    try:
        imdb_rating = float(soup.find('div', class_='ratingValue').find('span').string)
    except:
        imdb_rating = None
    # # Find the metascore of the movie if you want to use it
    # try:
    #     metascore = float(soup.find('div', class_="titleReviewBarItem").find('span').string)
    # except:
    #     # print('Accessing metascore failed.')
    #     metascore = None
    # Find the director, writer, star actors of the movie using bs4 and regex
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
            actors = None
    except:
        actors = None

    try:
        cast = actors.split(",")
    except:
        print("Cast not found")
    # Find the genres of the movie.
    try:
        genrediv = soup.find('div', class_='subtext')
        list_of_a_tags = genrediv.find_all('a')
        for a in list_of_a_tags:
            if (re.findall(r"\d{4}", a.string)):
                break
            genre_string += a.string + ','
        try:
            genre_string = genre_string[0:len(genre_string) - 1]
        except:
            genre_string = None
    except:
        genre_string = None
    try:
        genres = genre_string.split(',')
    except:
        print("Genres not found")
    # Find the Production House.
    try:
        divs = soup.find('div', id='titleDetails').find_all('div', class_='txt-block')
        h4_count = 0
        for div in divs:
            if (h4_count > 12):
                break
            if (div.find('h4', class_='inline').string == "Production Co:"):
                production_house = div.find('a').string.strip()
            h4_count += 1
    except:
        pass

    predicted_movie_rating = float(creating_model.predict(year_released, pred_runtime, genres, cast, production_house, director,
                                                    writer, IMDB, feature_columns, lm))
    predicted_movie_rating = round(predicted_movie_rating, 2)
    return predicted_movie_rating

def main():
    #Ask for the number of movies to be added
    number_of_movies = int(input("Enter the number of movies: "))
    for i in range(0,number_of_movies):
        #Ask for the name of movie and year of release
        movie_name = input("Enter name of movie: ")
        year_released = int(input("Enter year of release: "))
        print("The predicted rating is: ", predict_rating(movie_name,year_released))

if __name__ == '__main__':
    main()
