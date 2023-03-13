import json

import geopandas as gpd
import numpy as np
import pandas as pd
from bokeh.io import show, output_file
from bokeh.models import ColumnDataSource, ColorBar, HoverTool, Slope
from bokeh.models import GeoJSONDataSource, LinearColorMapper
from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.layouts import column, gridplot
import bokeh.palettes
from dataprep.clean import clean_country
from bokeh.palettes import brewer
from sklearn.linear_model import LinearRegression
import datetime

dir = "assignment1_data/"
year = "2021"


# useful functions
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
        df.rename(columns={"Order Charged Timestamp": "Transaction Time"}, inplace=True)
        df.rename(columns={"Financial Status": "Transaction Type"}, inplace=True)
        df.rename(columns={"Device Model": "Hardware"}, inplace=True)
        df.rename(columns={"Product ID": "Product id"}, inplace=True)
        df.rename(columns={"SKU ID": "Sku Id"}, inplace=True)
        df.rename(columns={"Currency of Sale": "Buyer Currency"}, inplace=True)
        df.rename(columns={"State of Buyer": "Buyer State"}, inplace=True)
        df.rename(columns={"Postal Code of Buyer": "Buyer Postal Code"}, inplace=True)
        df.rename(columns={"Country of Buyer": "Buyer Country"}, inplace=True)
        temp.append(df)

        i += 1

    return pd.concat(temp, ignore_index=True)


def filter_sales(inputdf):  # refunds compleet wegfilteren. Zowel voor transaction count als hoeveelheid geld handig
    temp = inputdf
    droplist = list()
    refunds = temp.loc[
        (temp["Transaction Type"] == "Charge refund") | (temp["Transaction Type"] == "Refund"), "Description"]
    for i in refunds:
        index = temp[temp["Description"] == i].index
        for j in index:
            droplist.append(j)

    temp = temp.drop(droplist)
    temp = temp[temp["Transaction Type"].isin(["Charge", "Charged"])]

    return temp


def count_transactions(inputdf):  # telt aantal transacties, gesplitst op Sku Id en totaal
    temp = inputdf[["Transaction Date", "Sku Id"]].value_counts(sort=False).copy()
    temp = temp.unstack(fill_value=0).reset_index(level=0)
    temp["Total Transaction Count"] = temp["premium"] + temp["unlockcharactermanager"]
    temp["offset8"] = temp["Transaction Date"] + pd.DateOffset(
        hours=8)  # tijd-offset nodig omdat het anders onmogelijk is meerdere bars te plotten per dag
    temp["offset12"] = temp["Transaction Date"] + pd.DateOffset(
        hours=12)  # x=dodge(...) werkt helaas echt ALLEEN met categorical data en niet met tijdframes
    temp["offset16"] = temp["Transaction Date"] + pd.DateOffset(hours=16)  # 8 & 16 zijn voor drie bars, 12 voor 2 bars

    return temp


def convert_to_weekdays(inputdf):
    temp = inputdf.copy()
    temp["Transaction Date"] = temp["Transaction Date"].dt.to_period(freq="W")
    temp = temp.drop(["offset8", "offset12", "offset16"], axis=1)
    temp = temp.groupby("Transaction Date").sum()
    temp.reset_index(inplace=True)
    temp["Period"] = temp["Transaction Date"].dt.strftime('%Y-%m-%d')
    temp["temp"] = temp["Period"].copy()
    temp["temp"] = pd.to_datetime(temp["temp"]) + pd.DateOffset(days=1)
    temp.iloc[30, 5] = "2021-12-31"
    temp["Period"] = temp["temp"].dt.strftime("%d-%m")
    temp["temp"] = temp["temp"] - pd.DateOffset(days=6)
    temp["Period"] = temp["temp"].dt.strftime(" %d-%m-\n") + temp["Period"]
    temp = temp.drop("temp", axis=1)

    return temp


def set_date(current_date):
    date_obj = pd.to_datetime(current_date)
    new_cntrs = data_countries[data_countries["Date"] == date_obj]
    merged = gdf.merge(new_cntrs, left_on="country_code", right_on="country_code",
                       how="left")
    merged["Date"] = merged["Date"].astype(str)
    json_countries_temp = json.loads(merged.to_json())
    json_countries_temp = json.dumps(json_countries_temp)
    return json_countries_temp


# Data import and cleaning
data_sales = import_csvs(dir + "sales_" + year, encoding="utf-8")
data_sales["Transaction Date"] = pd.to_datetime(data_sales["Transaction Date"])
data_sales.pop("Base Plan ID")
data_sales.pop("Offer ID")
sales_ddfive = data_sales[
    data_sales["Product id"] == "com.vansteinengroentjes.apps.ddfive"]  # andere apps eruit filteren
sales_norefunds = filter_sales(sales_ddfive)  # zonder refunds en zonder google fee
sales_count = count_transactions(sales_norefunds)
sales_count_weekperiods = convert_to_weekdays(sales_count)
data_sales = clean_country(data_sales, "Buyer Country", output_format="alpha-3")
data_sales.pop("Buyer Country")
data_sales.rename(columns={"Buyer Country_clean": "Buyer Country"}, inplace=True)
unique_dates = data_sales["Transaction Date"].unique()

data_reviews = import_csvs(dir + "reviews_" + year)
data_crashes = import_csvs(dir + "stats_crashes_" + year, "_overview")
data_ratings = import_csvs(dir + "stats_ratings_" + year, "_overview")

# Countries data cleaning
data_countries = import_csvs(dir + "stats_ratings_" + year, "_country")
data_countries["Date"] = pd.to_datetime(data_countries["Date"])
data_countries = clean_country(data_countries, "Country", output_format="alpha-3")
data_countries.rename(columns={"Country_clean": "country_code"}, inplace=True)
data_countries.pop("Country")
unique_countries = data_countries["country_code"].unique()

# pd.set_option('display.max_columns', None)
# pd.set_option('display.max_rows', None)

barplot_xrange = list(range(31))
for i in range(31):
    barplot_xrange[i] = sales_count_weekperiods["Period"][i]

sales_count_cds = ColumnDataSource(sales_count)
sales_count_cds2 = ColumnDataSource(sales_count)
sales_count_weekperiods_cds = ColumnDataSource(sales_count_weekperiods)

# Sales Volume Figure
output_file("visualization.html", title="Data Visualization")

fig1 = figure(title="Transaction count over time", x_axis_type="datetime", width=1900, x_axis_label="Date",
              y_axis_label="Transaction count")
fig2 = figure(title="Transaction count over time", x_axis_type="datetime", width=1900, x_axis_label="Date",
              y_axis_label="Transaction count")
fig3 = figure(title="Transaction count over time", width=1300, x_axis_label="Date",
              y_axis_label="Transaction count", x_range=barplot_xrange)

fig1.vbar(x="Transaction Date", bottom=0, top="premium", line_width=2, color='blue', legend_label="DM Tools",
          source=sales_count_cds)
fig1.vbar(x="offset8", bottom=0, top="unlockcharactermanager", line_width=2, color='red',
          legend_label="Character Manager", source=sales_count_cds)
fig1.vbar(x="offset16", bottom=0, top="Total Transaction Count", line_width=2, color='green', legend_label="Total",
          source=sales_count_cds)
fig1.legend.location = "top_left"
fig1.y_range.start = 0
fig1.x_range.start = sales_count["Transaction Date"][0] - pd.DateOffset(days=2)
fig1.x_range.end = sales_count["Transaction Date"][len(sales_count["Transaction Date"]) - 1] + pd.DateOffset(days=3)

fig2.vbar(x="Transaction Date", bottom=0, top="premium", line_width=2, color='blue', legend_label="DM Tools",
          source=sales_count_cds2)
fig2.vbar(x="offset12", bottom=0, top="unlockcharactermanager", line_width=2, color='red',
          legend_label="Character Manager", source=sales_count_cds2)
fig2.line("Transaction Date", "Total Transaction Count", color="green", line_width=1, legend_label="Total",
          source=sales_count_cds2)
fig2.legend.location = "top_left"
fig2.y_range.start = 0
fig2.x_range.start = sales_count["Transaction Date"][0] - pd.DateOffset(days=2)
fig2.x_range.end = sales_count["Transaction Date"][len(sales_count["Transaction Date"]) - 1] + pd.DateOffset(days=3)

fig3.line("Period", "Total Transaction Count", color="#78c679", line_width=2, legend_label="Total",
          source=sales_count_weekperiods_cds)
fig3.vbar(x=dodge("Period", -0.21, range=fig3.x_range), bottom=0, top="premium", width=0.35, color="#7fcdbb",
          legend_label="DM Tools", source=sales_count_weekperiods_cds)
fig3.vbar(x=dodge("Period", 0.21, range=fig3.x_range), bottom=0, top="unlockcharactermanager", width=0.35,
          color="#1d91c0", legend_label="Character Manager", source=sales_count_weekperiods_cds)
fig3.legend.location = "top_right"
fig3.y_range.start = 0
fig3.legend.orientation = "horizontal"
fig3.legend.background_fill_alpha = 0
fig3.legend.border_line_alpha = 0
fig3.y_range.start = 0

# Geographical Development
shapefile = 'countries_data/ne_110m_admin_0_countries.shp'

# Read shapefile using Geopandas
gdf = gpd.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
gdf.head()

# Drop row corresponding to 'Antarctica'
gdf = gdf.drop(gdf.index[159])
gdf.columns = ['country', 'country_code', 'geometry']
data_countries.rename(columns={"Total Average Rating": "TotalAverageRating"}, inplace=True)

# Adding some data to data_countries
data_countries["DailySales"] = 0
data_countries["SalesOverTime"] = 0
sales_list = filter_sales(data_sales)
data_sales.rename(columns={"Transaction Date": "Date"}, inplace=True)
data_sales.rename(columns={"Buyer Country": "Country"}, inplace=True)

for country in unique_countries:
    prev_sales = 0
    for date in unique_dates:
        daily_sales = len(data_sales[(data_sales["Date"] == date) & (data_sales["Country"] == country)])
        data_countries.loc[(data_countries["country_code"] == country) & (data_countries["Date"] == date), [
            "DailySales"]] = daily_sales
        data_countries.loc[(data_countries["country_code"] == country) & (data_countries["Date"] == date), [
            "SalesOverTime"]] = daily_sales + prev_sales
        prev_sales = prev_sales + daily_sales

# Merging geopandas geometry and the data
json_countries_start = set_date(datetime.date(2021, 6, 1))
json_countries_end = set_date(datetime.date(2021, 12, 31))

# Making the geopandas bokeh plot
geosource_countries_start = GeoJSONDataSource(geojson=json_countries_start)
geosource_countries_end = GeoJSONDataSource(geojson=json_countries_end)
palette = brewer['YlGn'][8]
palette = palette[::-1]
color_mapper_start = LinearColorMapper(palette=palette, nan_color='#d9d9d9',low=0, high=10)
color_mapper_end = LinearColorMapper(palette=palette, low=0, high=300, nan_color='#d9d9d9')
color_mapper_average_rating = LinearColorMapper(palette=palette, low=0, high=5, nan_color='#d9d9d9')

# Create color bar.
tick_labels = {'0': '0', '50': '50', '100': '100', '150': '150', '200': '200', '250': '250', '300': '300+'}
color_bar_start = ColorBar(color_mapper=color_mapper_start, label_standoff=8, width=500, height=20,
                     border_line_color=None, location=(0, 0), orientation='horizontal')
color_bar_end = ColorBar(color_mapper=color_mapper_end, label_standoff=8, width=500, height=20,
                     border_line_color=None, location=(0, 0), orientation='horizontal',
                     major_label_overrides=tick_labels)
color_bar_average_rating = ColorBar(color_mapper=color_mapper_average_rating, label_standoff=8, width=500, height=20,
                     border_line_color=None, location=(0, 0), orientation='horizontal')

# Create figure object.
geo_map_start = figure(title='Daily Sales at 2021-06-01', plot_height=400, plot_width=750, toolbar_location=None)
geo_map_end = figure(title='Sales over Time at 2021-12-31', plot_height=400, plot_width=750, toolbar_location=None)
geo_map_average_rating = figure(title='Total Average Rating per Country', plot_height=400, plot_width=750, toolbar_location=None)
geo_map_start.xgrid.grid_line_color = None
geo_map_start.ygrid.grid_line_color = None
geo_map_end.xgrid.grid_line_color = None
geo_map_end.ygrid.grid_line_color = None
geo_map_average_rating.xgrid.grid_line_color = None
geo_map_average_rating.ygrid.grid_line_color = None

# Add patch renderer to figure.
geo_map_patches_start = geo_map_start.patches('xs', 'ys', source=geosource_countries_start,
                                  fill_color={'field': 'DailySales', 'transform': color_mapper_start},
                                  line_color='black', line_width=0.25, fill_alpha=1)
geo_map_patches_end = geo_map_end.patches('xs', 'ys', source=geosource_countries_end,
                                  fill_color={'field': 'SalesOverTime', 'transform': color_mapper_end},
                                  line_color='black', line_width=0.25, fill_alpha=1)
geo_map_patches_average_rating = geo_map_average_rating.patches('xs', 'ys', source=geosource_countries_end,
                                  fill_color={'field': 'TotalAverageRating', 'transform': color_mapper_average_rating},
                                  line_color='black', line_width=0.25, fill_alpha=1)

# Specify figure layout.
geo_map_start.add_layout(color_bar_start, 'below')
geo_map_end.add_layout(color_bar_end, 'below')
geo_map_average_rating.add_layout(color_bar_average_rating, 'below')

# Create hover tool
geo_map_start.add_tools(HoverTool(renderers=[geo_map_patches_start],
                            tooltips=[('Country', '@country'),
                                      ('Total Average Rating', '@TotalAverageRating'),
                                      ('Sales over Time', '@SalesOverTime'),
                                      ('Daily Sales', '@DailySales')]))
geo_map_end.add_tools(HoverTool(renderers=[geo_map_patches_end],
                            tooltips=[('Country', '@country'),
                                      ('Total Average Rating', '@TotalAverageRating'),
                                      ('Sales over Time', '@SalesOverTime'),
                                      ('Daily Sales', '@DailySales')]))
geo_map_average_rating.add_tools(HoverTool(renderers=[geo_map_patches_average_rating],
                            tooltips=[('Country', '@country'),
                                      ('Total Average Rating', '@TotalAverageRating')]))

# Set up geomap layout
geo_layout = gridplot([[geo_map_start, geo_map_end], [geo_map_average_rating, None]])



#Making the KPI figure

#Data setup
data_ratings.rename(columns={"Daily Average Rating": "DailyAverageRating"}, inplace=True)
data_crashes.rename(columns={"Daily Crashes": "DailyCrashes"}, inplace=True)

merged_ratings_crashes = data_crashes.merge(data_ratings, left_on="Date", right_on="Date",
                       how="left")
merged_ratings_crashes = merged_ratings_crashes.dropna(subset=['DailyAverageRating', 'DailyCrashes'])
ratings_crashes_source = ColumnDataSource(merged_ratings_crashes)

#Prepare data for linear regression
x=merged_ratings_crashes["DailyCrashes"].to_numpy()
y=merged_ratings_crashes["DailyAverageRating"].to_numpy()

#Create linear regression model using scikit learn
linear_model = LinearRegression().fit(x.reshape(-1, 1), y)

#Get the slope and intercept from the model
slope = linear_model.coef_[0]
intercept = linear_model.intercept_

#Make the trend line
trend_line = Slope(gradient=slope, y_intercept=intercept,line_color='black')

#Create the tools for the figure
select_tools = ['box_select', 'lasso_select', 'poly_select', 'tap', 'reset']

#Creating the figure
number_of_crashes_vs_ratings = figure(plot_height=500,
                                      plot_width=500,
                                      x_axis_label='Daily Crashes',
                                      y_axis_label='Daily Average Rating',
                                      title='Number of Crashes vs Daily Average Rating, 2021-06 - 2021-12',
                                      toolbar_location='below',
                                      tools=select_tools)

#Add the data points to the figure
number_of_crashes_vs_ratings.square(x='DailyCrashes',
                                    y='DailyAverageRating',
                                    source=ratings_crashes_source,
                                    color='royalblue',
                                    selection_color='deepskyblue',
                                    nonselection_color='lightgray',
                                    nonselection_alpha=0.3)

#Making a hover renderer
hover_circles = number_of_crashes_vs_ratings.circle(x='DailyCrashes', y='DailyAverageRating',
                                                    source=ratings_crashes_source,
                                                    size=15, alpha=0,
                                                    hover_fill_color='black', hover_alpha=0.5)

#Add the trend line
number_of_crashes_vs_ratings.add_layout(trend_line)

#Create tooltips for the hover tool
tooltips = [
    ('Date', '@Date'),
    ('Daily Average Rating', '@DailyAverageRating'),
    ('Daily Crashes', '@DailyCrashes')
]

number_of_crashes_vs_ratings.add_tools(HoverTool(tooltips=tooltips, renderers=[hover_circles]))
kpi_figure = column(number_of_crashes_vs_ratings)

print(data_countries.loc[data_countries['Daily Average Rating'] < 4, ['country_code']].value_counts().nlargest(1))
p = column(fig3, kpi_figure, geo_layout)
# Generate the HTMLre, geo_layout)
show(p)
