import json

import geopandas as gpd
import pandas as pd
from bokeh.io import show, output_file
from bokeh.models import ColumnDataSource, ColorBar
from bokeh.models import GeoJSONDataSource, LinearColorMapper
from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.layouts import gridplot, column
import bokeh.palettes
from dataprep.clean import clean_country
from bokeh.palettes import brewer

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

def filter_sales(inputdf): # refunds compleet wegfilteren. Zowel voor transaction count als hoeveelheid geld handig
    temp = inputdf
    droplist = list()
    refunds = temp.loc[(temp["Transaction Type"] == "Charge refund") | (temp["Transaction Type"] == "Refund"), "Description"]
    for i in refunds:
        index = temp[temp["Description"] == i].index
        for j in index:
            droplist.append(j)

    temp = temp.drop(droplist)

    return temp


def count_transactions(inputdf): # telt aantal transacties, gesplitst op Sku Id en totaal
    temp = inputdf[inputdf["Transaction Type"].isin(["Charge", "Charged"])]
    temp = temp[["Transaction Date", "Sku Id"]].value_counts(sort=False).copy()
    temp = temp.unstack(fill_value=0).reset_index(level=0)
    temp["Total Transaction Count"] = temp["premium"]+temp["unlockcharactermanager"]
    temp["offset8"] = temp["Transaction Date"] + pd.DateOffset(hours=8)  # tijd-offset nodig omdat het anders onmogelijk is meerdere bars te plotten per dag
    temp["offset12"] = temp["Transaction Date"] + pd.DateOffset(hours=12)  # x=dodge(...) werkt helaas echt ALLEEN met categorical data en niet met tijdframes
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
    temp["Period"] = temp["temp"].dt.strftime("%m-%d")
    temp["temp"] = temp["temp"] - pd.DateOffset(days=6)
    temp["Period"] = temp["temp"].dt.strftime("  %m-%d -\n") + temp["Period"]
    temp = temp.drop("temp", axis=1)

    return temp


#Data
data_sales = import_csvs(dir + "sales_" + year, encoding="utf-8")
data_sales["Transaction Date"] = pd.to_datetime(data_sales["Transaction Date"])
data_sales.pop("Base Plan ID")
data_sales.pop("Offer ID")
sales_ddfive = data_sales[data_sales["Product id"] == "com.vansteinengroentjes.apps.ddfive"]    #andere apps eruit filteren
sales_norefunds = filter_sales(sales_ddfive) # zonder refunds, originele dataset wel gehouden om later nog shit met refunds te kunnen doen
sales_count = count_transactions(sales_norefunds)
sales_count_weekperiods = convert_to_weekdays(sales_count)

data_reviews = import_csvs(dir + "reviews_" + year)

data_crashes = import_csvs(dir + "stats_crashes_" + year, "_overview")
data_ratings = import_csvs(dir + "stats_ratings_" + year, "_overview")

data_countries = import_csvs(dir + "stats_ratings_" + year, "_country")

#pd.set_option('display.max_columns', None)
#pd.set_option('display.max_rows', None)

barplot_xrange = list(range(31))
for i in range(31):
    barplot_xrange[i] = sales_count_weekperiods["Period"][i]

sales_count_cds = ColumnDataSource(sales_count)
sales_count_cds2 = ColumnDataSource(sales_count)
sales_count_weekperiods_cds = ColumnDataSource(sales_count_weekperiods)

#Sales Volume Figure
output_file("visualization.html", title="Placeholder")

fig1 = figure(title="Transaction count over time", x_axis_type="datetime", width=1900, x_axis_label="Date", y_axis_label="Transaction count")
fig2 = figure(title="Transaction count over time", x_axis_type="datetime", width=1900, x_axis_label="Date", y_axis_label="Transaction count")
fig3 = figure(title="Transaction count over time", sizing_mode="stretch_width", x_axis_label="Date", y_axis_label="Transaction count", x_range=barplot_xrange)

fig1.vbar(x="Transaction Date", bottom=0, top="premium", line_width=2, color='blue', legend_label="Premium", source=sales_count_cds)
fig1.vbar(x="offset8", bottom=0, top="unlockcharactermanager", line_width=2, color='red', legend_label="Unlock", source=sales_count_cds)
fig1.vbar(x="offset16", bottom=0, top="Total Transaction Count", line_width=2, color='green', legend_label="Total", source=sales_count_cds)
fig1.legend.location = "top_left"
fig1.y_range.start = 0
fig1.x_range.start = sales_count["Transaction Date"][0]-pd.DateOffset(days=2)
fig1.x_range.end = sales_count["Transaction Date"][len(sales_count["Transaction Date"])-1]+pd.DateOffset(days=3)

fig2.vbar(x="Transaction Date", bottom=0, top="premium", line_width=2, color='blue', legend_label="Premium", source=sales_count_cds2)
fig2.vbar(x="offset12", bottom=0, top="unlockcharactermanager", line_width=2, color='red', legend_label="Unlock", source=sales_count_cds2)
fig2.line("Transaction Date", "Total Transaction Count", color="green", line_width=1, legend_label="Total", source=sales_count_cds2)
fig2.legend.location = "top_left"
fig2.y_range.start = 0
fig2.x_range.start = sales_count["Transaction Date"][0]-pd.DateOffset(days=2)
fig2.x_range.end = sales_count["Transaction Date"][len(sales_count["Transaction Date"])-1]+pd.DateOffset(days=3)

fig3.vbar(x=dodge("Period", -0.3, range=fig3.x_range), bottom=0, top="premium", width=0.25, color='blue', legend_label="Premium", source=sales_count_weekperiods_cds)
fig3.vbar(x=dodge("Period", 0.0, range=fig3.x_range), bottom=0, top="unlockcharactermanager", width=0.25, color='red', legend_label="Unlock", source=sales_count_weekperiods_cds)
fig3.vbar(x=dodge("Period", 0.3, range=fig3.x_range), bottom=0, top="Total Transaction Count", width=0.25, color='green', legend_label="Total", source=sales_count_weekperiods_cds)
fig3.legend.location = "top_left"
fig3.y_range.start = 0

#Geographical Development
shapefile = 'countries_data/ne_110m_admin_0_countries.shp'

#Read shapefile using Geopandas
gdf = gpd.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
gdf.head()

#Drop row corresponding to 'Antarctica'
gdf = gdf.drop(gdf.index[159])
gdf.columns = ['country', 'country_code', 'geometry']

#Converting country labels to ISO 3
cntrs = clean_country(data_countries[["Country", "Total Average Rating"]], "Country", output_format="alpha-3")
cntrs.rename(columns={"Country_clean": "country_code"}, inplace=True)


#Merging geopandas geometry and the data
merged = gdf.merge(cntrs[["country_code", "Total Average Rating"]], left_on = "country_code", right_on = "country_code")

json_countries = json.loads(merged[["country", "country_code", "geometry", "Total Average Rating"]].to_json())
json_countries = json.dumps(json_countries)

#Making the geopandas bokeh plot
geosource_countries = GeoJSONDataSource(geojson = json_countries)
palette = brewer['YlGnBu'][8]
palette = palette[::-1]
color_mapper = LinearColorMapper(palette = palette, low = 0, high = 5)

tick_labels = {'0': '0', '1': '1', '2':'2', '3':'3', '4':'4', '5':'5'}

#Create color bar.
color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 500, height = 20,
border_line_color=None,location = (0,0), orientation = 'horizontal', major_label_overrides = tick_labels)

#Create figure object.
geo_map = figure(title = 'Stats per Country', plot_height = 600 , plot_width = 950, toolbar_location = None)
geo_map.xgrid.grid_line_color = None
geo_map.ygrid.grid_line_color = None

#Add patch renderer to figure.
geo_map.patches('xs','ys', source = geosource_countries,fill_color = {'field' :'Total Average Rating', 'transform' : color_mapper},
          line_color = 'black', line_width = 0.25, fill_alpha = 1)

#Specify figure layout.
geo_map.add_layout(color_bar, 'below')


p = column(fig1, geo_map)
show(p)
#show(fig3)
