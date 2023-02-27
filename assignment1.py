import pandas as pd
import numpy as np
import geopandas as gp
from bokeh.io import output_file, output_notebook
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource
from bokeh.layouts import row, column, gridplot

dir = "assignment1_data/"
year = "2021"

#useful functions
def import_csvs(name, suffix="", encoding="utf-16"):
    temp = list()

    i = 6
    while i < 13:
        if i < 10:
            j = "0" + str(i)
        else:
            j = str(i)

        df = pd.read_csv(name + j + suffix + ".csv", encoding=encoding)
        df.rename(columns={"Order Number": "Description"}, inplace=True)
        df.rename(columns={"Order Charged Date": "Transaction Date"}, inplace=True)
        temp.append(df)

        i += 1

    return pd.concat(temp, ignore_index=True)



#Data
data_sales = import_csvs(dir + "sales_" + year, encoding="utf-8")
data_sales["Transaction Date"] = pd.to_datetime(data_sales["Transaction Date"])

data_reviews = import_csvs(dir + "reviews_" + year)

data_crashes = import_csvs(dir + "stats_crashes_" + year, "_overview")
data_ratings = import_csvs(dir + "stats_ratings_" + year, "_overview")


import_csvs(dir + "stats_ratings_" + year, "_country")



#Sales Volume Figure
output_file("visualization.html", title="Placeholder")
#output_notebook()

#source = ColumnDataSource(data_ratings)

#fig = figure(source=source)

#show(fig)



