import numpy as np
from numpy import cov
import pandas as pd
import time
import sys
from random import seed,randint
import re
from sklearn.metrics import r2_score,mean_squared_error,mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from math import isnan
from warnings import filterwarnings
import pickle
filterwarnings("ignore")

#These helper functions are used for dealing with categorical values.

#Used for finding the average Imdb rating of the movie produced by production houses.
def alt_production_mapping(production_group,col):
    return production_group.get_group(col)['IMDB Rating'].mean()

#Used for finding the average Imdb rating of the movie of directors.
def alt_director_mapping(director_group,col):
    return director_group.get_group(col)['IMDB Rating'].mean()

#Used for finding the average Imdb rating of the movie of writers.
def alt_writer_mapping(writer_group,col):
    return writer_group.get_group(col)['IMDB Rating'].mean()

#We will only use the features which are available prior to the release of movie.
#Since I didnt know whether metascore is available or not, I decided to exclude it from consideration.
def predict(year,runtime,genres,cast,production_house,director,writer,IMDB,feature_columns,lm):
    arr = np.zeros((28,))
    actor_score = 0
    actor_count = len(cast)
    arr[0] = year
    if (runtime != None):
        arr[1] = runtime
    else:
        arr[1] = IMDB['Runtime (Minutes)'].mean()
    for genre in genres:
        index = np.where(feature_columns == genre)
        arr[index] = 1
    nan_count_for_cast=actor_count
    for actor in cast:
        value = IMDB[IMDB['Cast'].str.contains(actor)]['IMDB Rating'].mean()
        if(isnan(value)):
            nan_count_for_cast-=1
        else:
            actor_score+=value

    if(nan_count_for_cast==0):
        actor_score = IMDB['Avg Actor Rating'].mean()
    else:
        actor_score = actor_score / actor_count
    actor_score = actor_score / actor_count
    arr[24] = actor_score
    try:
        arr[25] = IMDB[IMDB['Production House'] == production_house]['Production House Score'].iloc[0]
    except:
        arr[25] = IMDB['Production House Score'].mean()
    try:
        arr[26] = IMDB[IMDB['Director'] == director]['Director Score'].iloc[0]
    except:
        arr[26] = IMDB['Director Score'].mean()
    try:
        arr[27] = IMDB[IMDB['Writer'] == writer]['Writer Score'].iloc[0]
    except:
        arr[27] = IMDB['Writer Score'].mean()

    #Return the predicted value.
    return lm.predict([arr])[0]

def create_model():
    try:
        #If the model already exists then we will use it.
        pickled_model, pickled_data, pickled_columns = pickle.load(open("imdb_model.pkl","rb"))
        print("Pickle exists.")
        return pickled_model, pickled_data, pickled_columns
    except:
        print("Pickle being created.")
        IMDB = pd.read_csv("movie_ratings.csv", sep=',')
        #Drop null values from the genres. The EDA is done in the Jupyter notebook file.
        IMDB['Genres'].dropna(inplace=True)
        try:
            IMDB.drop('Unnamed: 0', axis=1, inplace=True)
        except:
            pass
        IMDB = IMDB.reset_index(drop=True)

        # Removing useless genres which increase the number of features for no advantage at all
        # This keeps giving error till run multiple times for some unknown reason so used a while loop since the size of dataset is small.
        flag = 0
        while flag == 0:
            try:
                for i in range(0, len(IMDB)):
                    if (isinstance(IMDB.iloc[i]['Genres'], str)):
                        array = IMDB.iloc[i]['Genres'].split(',')
                        removal = ['Video\n','TV Movie\n','TV Series\n','Talk-show', 'News', 'Film-Noir', 'Game-Show',
                                   'See all in-development titles on IMDbPro', 'Talk-Show', 'Video', 'Reality-TV',
                                   'TV Movie', 'TV Episode', 'TV Series']
                        check = any(item in removal for item in array)
                        if (check):
                            IMDB.drop(IMDB.index[i], axis=0, inplace=True)
                flag = 1
            except:
                flag = 0
        genres = []
        i = 0
        for i in range(0, len(IMDB)):
            if (isinstance(IMDB.iloc[i]['Genres'], str)):
                array = IMDB.iloc[i]['Genres'].split(',')
                for j in array:
                    genres.append(j)
        genres = list(dict.fromkeys(genres))
        # Add the columns of the genres
        for genre in genres:
            IMDB[genre] = 0
        # Add the values of the genres
        IMDB = IMDB.reset_index(drop=True)
        for i in range(0, len(IMDB)):
            if (isinstance(IMDB.iloc[i]['Genres'], str)):
                genre_array = IMDB.iloc[i]['Genres'].split(',')
                for genre in genre_array:
                    IMDB[genre].iloc[i] = 1
        IMDB.drop(['Budget', 'USA Revenue', 'Worldwide Revenue'], axis=1, inplace=True)
        IMDB.drop(['Metacritic Users', 'Metacritic Critics'], axis=1, inplace=True)
        # The information below cannot be used since it is not available at the time of release of movie.
        IMDB.drop(['IMDB Votes'], inplace=True, axis=1)
        IMDB.drop(['Metascore'],inplace=True,axis=1)
        # Dropping all the null values.
        IMDB.dropna(inplace=True)
        # Creating a column for average imdb rating of the stars combined.
        IMDB['Avg Actor Rating'] = 0
        # Assigning Avg Actor Rating Of Each Movie
        # Create a dictionary so that if an actor already exists then the rating is accessed straight away.
        actors_rating = {}
        for i in range(0, len(IMDB)):
            if (isinstance(IMDB.iloc[i]['Cast'], str)):
                actor_array = IMDB.iloc[i]['Cast'].split(',')
                actor_count = len(actor_array)
                actor_score = 0
                for actor in actor_array:
                    if actor in actors_rating:
                        actor_score += actors_rating[actor]
                    else:
                        actor_score += IMDB[IMDB['Cast'].str.contains(actor)]['IMDB Rating'].mean()
                        actors_rating[actor] = actor_score
                actor_score = actor_score / actor_count
                IMDB['Avg Actor Rating'].iloc[i] = actor_score

        # Create the groups of production houses,directors and writers.
        production_group = IMDB.groupby("Production House")
        director_group = IMDB.groupby('Director')
        writer_group = IMDB.groupby('Writer')
        # Create the columns of the scores.
        IMDB['Production House Score'] = 0
        IMDB['Director Score'] = 0
        IMDB['Writer Score'] = 0
        # Map the values
        IMDB['Production House Score'] = IMDB['Production House'].map(lambda x: alt_production_mapping(production_group, x))
        IMDB['Director Score'] = IMDB['Director'].map(lambda x: alt_director_mapping(director_group, x))
        IMDB['Writer Score'] = IMDB['Writer'].map(lambda x: alt_writer_mapping(writer_group, x))

        feature_columns = IMDB.drop(['Movie Name', 'IMDB Rating', 'Genres', 'Cast', 'Director', 'Writer', 'Production House'], axis=1).columns
        X = IMDB.drop(['Movie Name','IMDB Rating','Genres','Cast','Director','Writer','Production House'],axis=1)
        y = np.array(IMDB['IMDB Rating']).reshape(-1, 1)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
        lm=LinearRegression()
        lm.fit(X, y.ravel())
        y_pred = lm.predict(X_test)
        print("R2 Score=",str(r2_score(y_test,y_pred)))
        # Create pickle if it doesnt exist
        pickle_name = "imdb_model.pkl"
        pickle.dump((lm,IMDB,feature_columns),open(pickle_name,"wb"))
        # Return the pickled values
        pickled_model, pickled_data, pickled_columns = pickle.load(open("imdb_model.pkl", "rb"))
        return pickled_model, pickled_data, pickled_columns

def main():
    print("creating_model.py file started/imported.")

if __name__=='__main__':
    main()

if __name__!='__main__':
    main()