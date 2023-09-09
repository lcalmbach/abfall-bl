import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from os.path import exists
from datetime import datetime, timedelta, date
from utilities import load_css
import requests
import io
import pytz
import numpy as np
import math

import plots
import text

__version__ = "0.0.1"
__author__ = "Lukas Calmbach"
__author_email__ = "lcalmbach@gmail.com"
VERSION_DATE = "2023-09-03"
my_title = "Abfall-BL"
my_icon = "🛢️"
SOURCE_URL = "https://data.bl.ch/api/explore/v2.1/catalog/datasets/12060/exports/csv?lang=de&timezone=Europe%2FParis&use_labels=false&delimiter=%3B"
SOURCE_FILE = "./12060.csv"
SOURCE_BEV_URL = "./10040.csv"
GIT_REPO = "https://github.com/lcalmbach/abfall-bl"
YEARS = range(2018, date.today().year)
utc = pytz.UTC

KEHRICHT = "Hauskehricht + Sperrgut"

def init():
    st.set_page_config(  # Alternate names: setup_page, page, layout
        initial_sidebar_state="auto",
        page_title=my_title,
        page_icon=my_icon,
        layout="wide"
    )
    load_css()


def get_filter(filter: dict, df: pd.DataFrame):
    options_einheit = df["einheit"].unique()
    options_gemeinden = df["gemeinde"].unique()
    options_kategorie = df["kategorie"].unique()
    filtered_df = df.copy()
    with st.sidebar.expander("🔎 Filter", expanded=True):
        if "jahr" in filter:
            filter["jahr"] = st.selectbox("Jahr", options=YEARS)
            filtered_df = filtered_df[filtered_df["jahr"] == filter["jahr"]]
        if "einheit" in filter:
            filter["einheit"] = st.selectbox("Einheit", options=options_einheit)
            filtered_df = filtered_df[filtered_df["einheit"] == filter["einheit"]]
        if "gemeinde" in filter:
            filter["gemeinde"] = st.selectbox("Gemeinde", options=options_gemeinden)
            filtered_df = filtered_df[filtered_df["gemeinde"] == filter["gemeinde"]]
        elif "gemeinden" in filter:
            filter["gemeinden"] = st.multiselect("Gemeinden", options=options_gemeinden)
            if filter["gemeinden"] != []:
                filtered_df = filtered_df[
                    filtered_df["gemeinde"].isin(filter["gemeinden"])
                ]
        if "kategorien" in filter:
            filter["kategorien"] = st.multiselect(
                "Abfall-Kategorien", options=options_kategorie
            )
            if filter["kategorien"] != []:
                filtered_df = filtered_df[
                    filtered_df["kategorie"].isin(filter["kategorien"])
                ]
        elif "kategorie" in filter:
            filter["kategorie"] = st.selectbox(
                "Abfall-Kategorie", options=options_kategorie
            )
            filtered_df = filtered_df[filtered_df["kategorie"] == filter["kategorie"]]

    return filter, filtered_df


def get_info():
    text = f"""<div style="background-color:#34282C; padding: 10px;border-radius: 15px; border:solid 1px white;">
    <small>App von <a href="mailto:{__author_email__}">{__author__}</a><br>
    Version: {__version__} ({VERSION_DATE})<br>
    Datenquelle: <a href="https://data.bl.ch/explore/dataset/12060/">OGD Baselland</a><br>
    <a href="{GIT_REPO}">git-repo</a></small></div>
    """
    return text


@st.cache_data(ttl=6 * 3600, max_entries=3)
def get_data():
    # df = pd.read_csv(SOURCE_FILE, sep=';')
    # if df[jahr]
    df = pd.read_csv(SOURCE_URL, sep=";")
    df = df[df['jahr'] > 2017]
    df_bev = pd.read_csv(SOURCE_BEV_URL, sep=";")
    df_bev = df_bev[["jahr", "gemeinde_nummer", "gemeinde", "endbestand"]]
    df_bev = df_bev[df_bev["jahr"] > 2017]
    return df, df_bev


def info(df):
    st.image("./waste.jpg")
    st.subheader("Abfallmengen und Recycling in den Gemeinden des Kantons Baselland")
    st.markdown(text.INTRO)


def stat_commune(df):
    st.subheader("Abfallmengen und Recycling nach Gemeinde")
    filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorien": None}
    filter, filtered_df = get_filter(filter, df)
    pivot_df = filtered_df.pivot(
        index="gemeinde", columns=["kategorie"], values=["wert"]
    ).reset_index()
    cols = [x[1] for x in pivot_df.columns]
    cols[0] = "gemeinde"
    pivot_df.columns = cols
    st.markdown(f"Einheit: {filter['einheit']}, Jahr: {filter['jahr']}")
    st.dataframe(pivot_df, hide_index=True)

    st.markdown("Statistik nach Abfall-Kategorie")
    group_fields = ["kategorie"]
    category_df = (
        filtered_df.groupby(group_fields)["wert"]
        .agg(["min", "max", "mean"])
        .reset_index()
    )
    category_df.columns = ["Kategorie", "Minimum", "Maximum", "Mittelwert"]
    st.dataframe(category_df, hide_index=True)


def show_plots(df):
    plot_options = ["Balkendiagramm", "Histogramm", "Zeitserie"]
    plot = st.sidebar.selectbox(label="Grafik", options=plot_options)
    if plot_options.index(plot) == 0:
        show_mean = st.sidebar.checkbox("zeige Mittelwert als Linie")
        filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        settings = {
            "x": "gemeinde",
            "y": "wert:Q",
            "x_title": filter["kategorie"],
            "y_title": filter["einheit"],
            "tooltip": ["jahr", "gemeinde", "wert"],
            "width": 800,
            "height": 600,
            "title": f"Balkendiagramm ({filter['kategorie']})",
        }
        if show_mean:
            mean = filtered_df[filtered_df["wert"] > 0]["wert"].mean()
            filtered_df["mittelwert"] = mean
            settings["h_line"] = "mittelwert"
        plots.barchart(filtered_df, settings)
    elif plot_options.index(plot) == 1:
        filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        settings = {
            "x": "wert:Q",
            "y": "count()",
            "x_title": filter["einheit"],
            "y_title": "Anzahl Gemeinden",
            "tooltip": ["jahr", "gemeinde", "wert"],
            "width": 800,
            "height": 400,
            "title": f"Histogramm ({filter['kategorie']})",
        }
        plots.histogram(filtered_df, settings)
    elif plot_options.index(plot) == 2:
        filter = {"einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        settings = {
            "x": "jahr",
            "x_dt": "N",
            "color": "gemeinde",
            "y": "wert",
            "y_dt": "Q",
            "x_title": filter["kategorie"],
            "y_title": filter["einheit"],
            "tooltip": ["jahr", "gemeinde", "wert"],
            "width": 800,
            "height": 600,
            "title": f"Zeitserie ({filter['kategorie']})",
        }
        plots.line_chart(filtered_df, settings)

def get_total_df(_df, gemeinde):
        if gemeinde != None:
            _df = _df[_df['gemeinde'] == gemeinde]
            _df = _df[['jahr', 'wert']]
            result = _df.groupby('jahr').sum().reset_index()
        else:
            _df = _df[['gemeinde', 'jahr', 'wert']]
            result = _df.groupby(['gemeinde', 'jahr']).sum().reset_index()
        return result


def get_gemeinde_rank(df, gemeinde):
    df['rang'] = df["wert"].rank(ascending=False)
    return df[df['gemeinde'] == gemeinde].iloc[0]['rang']


def get_general_text(df_kg, df_t, gemeinde):
    total_gemeinde_t_df = get_total_df(df_t, gemeinde)
    kehricht = "Hauskehricht + Sperrgut"
    first_year_waste_t = total_gemeinde_t_df[
        (total_gemeinde_t_df["jahr"] == YEARS[0])
    ].iloc[0]["wert"].round(0)
    last_year_waste_t = total_gemeinde_t_df[
        (total_gemeinde_t_df["jahr"] == YEARS[-1])
    ].iloc[0]["wert"].round(0)
    qualifier_diff_t = (
        "mehr" if last_year_waste_t > first_year_waste_t else "weniger"
    )

    total_gemeinde_kg_df = get_total_df(df_kg, gemeinde)
    
    first_year_waste_kg = total_gemeinde_kg_df[
        (total_gemeinde_kg_df["jahr"] == YEARS[0])
    ].iloc[0]["wert"].round(0)
    last_year_waste_kg = total_gemeinde_kg_df[
        (total_gemeinde_kg_df["jahr"] == YEARS[-1])
    ].iloc[0]["wert"].round(0)
    qualifier_diff_kg = (
        "stieg" if last_year_waste_kg > first_year_waste_kg else "sank"
    )
    increase_pct = abs(first_year_waste_t - last_year_waste_t) / first_year_waste_t
    rank_basis_df = get_total_df(df_kg, None)
    rank_basis_df = rank_basis_df[rank_basis_df['jahr'] == YEARS[-1]]
    rank = get_gemeinde_rank(rank_basis_df, gemeinde)
    text = f"""Die Gemeinde {gemeinde} hat im Jahr {YEARS[-1]} {last_year_waste_t: .1f} Tonnen Abfall 
    produziert, {abs(last_year_waste_t - first_year_waste_t)} Tonnen {qualifier_diff_t} als in {YEARS[0]}. Der pro Kopf Verbrauch {qualifier_diff_kg}
    von  {first_year_waste_kg} kg/Kopf in {YEARS[0]} auf {last_year_waste_kg} kg/Kopf in {YEARS[-1]} ({increase_pct * 100: .1f}%). Unter den Gemeinden des Kantons Baselland belegt 
    {gemeinde} beim Total des Abfalls in {YEARS[-1]} auf Rang {rank:.0f} von {rank_basis_df['rang'].max():.0f}.
    """
    return text


def get_category_text(df_t, df_kg, kategorie, gemeinde):
    df_kg["rank"] = df_kg["wert"].rank(ascending=False)
    df_t["rank"] = df_t["wert"].rank(ascending=False)
    generate_expr = 'produziert' if kategorie == KEHRICHT else 'gerecycelt'
    consumption_expr = 'Verbrauch' if kategorie == KEHRICHT else 'Recycling'
    
    first_year_t = df_t[(df_t["jahr"] == YEARS[0]) & (df_t["gemeinde"] == gemeinde)].iloc[0]["wert"]
    last_year_t = df_t[(df_t["jahr"] == YEARS[-1]) & (df_t["gemeinde"] == gemeinde)].iloc[0]["wert"]
    first_year_kg = df_kg[(df_kg["jahr"] == YEARS[0]) & (df_kg["gemeinde"] == gemeinde)].iloc[0]["wert"]
    last_year_kg = df_kg[(df_kg["jahr"] == YEARS[-1]) & (df_kg["gemeinde"] == gemeinde)].iloc[0]["wert"]
    rank_basis_df = get_total_df(df_kg, None)
    rank_basis_df = rank_basis_df[rank_basis_df['jahr'] == YEARS[-1]]
    rank = get_gemeinde_rank(rank_basis_df, gemeinde)
    if last_year_t > 0:
        text = f"""**{kategorie}**: Es wurden in {YEARS[-1]} in {gemeinde} {last_year_t: .1f} Tonnen {kategorie} {generate_expr}, dies entspricht
        {last_year_kg: .1f} kg/Kopf. Im Ranking der Gemeinden erreicht {gemeinde} beim pro Kopf {consumption_expr} von {kategorie} Platz {rank: .0f}.
        """
    else:
        text = ""
    return text


def show_commune_report(df):
    options_gemeinden = sorted(list(df["gemeinde"].unique()))
    options_kategorie = sorted(list(df["kategorie"].unique()))
    gemeinde = st.sidebar.selectbox("Gemeinde", options=options_gemeinden)
    kateborie = st.sidebar.selectbox("Kategorie", options=options_kategorie)
    st.subheader(f"Zusammenfassung Gemeinde {gemeinde}")
    
    df_kg = df[df["einheit"] == "kg pro Einw."]
    df_t = df[df["einheit"] == "Tonnen"]
    st.markdown("**Abfall total**")
    text = get_general_text(df_kg, df_t, gemeinde)
    st.markdown(text)
    for kategorie in options_kategorie:
        df_kategorie_t = df_t[df['kategorie'] == kategorie]
        df_kategorie_kg = df_kg[df['kategorie'] == kategorie]
        text = get_category_text(df_kategorie_t, df_kategorie_kg, kategorie, gemeinde)
        if text > "":
            st.markdown(text)


def main():
    """
    main menu with 3 options: cum consumption year of day, mean daily consumption in week
    and mean 1/4 consumption in day for selected period and years
    """
    init()
    df, df_bev = get_data()
    st.sidebar.markdown(f"### {my_icon} {my_title}")

    menu_options = ["Info", "Statistik nach Gemeinde", "Grafiken", "Gemeinde-Bericht"]
    # https://icons.getbootstrap.com/
    with st.sidebar:
        menu_action = option_menu(
            None,
            menu_options,
            icons=["info-square", "table", "graph-up", "houses"],
            menu_icon="cast",
            default_index=0,
        )

    if menu_action == menu_options[0]:
        info(df)
    elif menu_action == menu_options[1]:
        stat_commune(df)
    elif menu_action == menu_options[2]:
        show_plots(df)
    elif menu_action == menu_options[3]:
        show_commune_report(df)

    st.sidebar.markdown(get_info(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
