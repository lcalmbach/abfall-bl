import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date
import os

import plots
import text
from utilities import load_css

__version__ = "0.0.6"
__author__ = "Lukas Calmbach"
__author_email__ = "lcalmbach@gmail.com"
VERSION_DATE = "2023-09-12"
my_title = "Abfall-BL"
my_icon = "♻️"

SOURCE_URL = "https://data.bl.ch/api/explore/v2.1/catalog/datasets/12060/exports/csv?lang=de&timezone=Europe%2FParis&use_labels=false&delimiter=%3B"
SOURCE_BEV_URL = "https://data.bl.ch/api/explore/v2.1/catalog/datasets/10040/exports/csv?lang=de&timezone=Europe%2FParis&use_labels=false&delimiter=%3B"
GIT_REPO = "https://github.com/lcalmbach/abfall-bl"
LOCAL_DATA_WASTE = './local_data_waste.parquet'
LOCAL_DATA_BEV = './local_data_bev.parquet'
YEARS = range(2018, date.today().year)
KEHRICHT = "Hauskehricht + Sperrgut"
FIRST_YEAR = 2018
INTRO_IMAGE = "./waste.jpg"
UNITS = {"menge_t": "Tonnen", "menge_kg_pro_kopf": "kg pro Kopf"}


def init():
    st.set_page_config(  # Alternate names: setup_page, page, layout
        initial_sidebar_state="auto",
        page_title=my_title,
        page_icon=my_icon,
        layout="wide",
    )
    load_css()


def get_filter(filter: dict, df: pd.DataFrame):
    options_gemeinden = sorted(df["gemeinde"].unique())
    options_kategorie = df["kategorie"].unique()
    filtered_df = df.copy()
    with st.sidebar.expander("🔎 Filter", expanded=True):
        if "jahr" in filter:
            filter["jahr"] = st.selectbox("Jahr", options=YEARS)
            filtered_df = filtered_df[filtered_df["jahr"] == filter["jahr"]]
        if "einheit" in filter:
            filter["einheit"] = st.selectbox(
                label="Einheit", options=UNITS.keys(), format_func=UNITS.get
            )
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


def get_show_intro():
    """
    Processes the show intro menu item, desplaying a introductory text.
    """
    text = f"""<div style="background-color:#34282C; padding: 10px;border-radius: 15px; border:solid 1px white;">
    <small>App von <a href="mailto:{__author_email__}">{__author__}</a><br>
    Version: {__version__} ({VERSION_DATE})<br>
    Datenquelle: <a href="https://data.bl.ch/explore/dataset/12060/">OGD Basel-Landschaft</a><br>
    <a href="{GIT_REPO}">git-repo</a></small></div>
    """
    return text


@st.cache_data(ttl=6 * 3600, max_entries=3)
def get_data():
    """
    Retrieves waste data and population data from local files or online sources.
    If the local data file exists, it reads the data from the file, otherwise it downloads
    the data from the specified URL. It then processes the population data is merged 
    into the waste data and saved as a parquet file and returns the merged DataFrame and 
    the population DataFrame.

    Returns:
        merged_df (pandas.DataFrame): Merged DataFrame containing waste data and population data
        pop_df (pandas.DataFrame): DataFrame containing population data

    """

    if os.path.exists(LOCAL_DATA_WASTE):
        merged_df = pd.read_parquet(LOCAL_DATA_WASTE)
        pop_df = pd.read_parquet(LOCAL_DATA_WASTE)
    else:
        # read waste data
        waste_df = pd.read_csv(SOURCE_URL, sep=";")
        # pivot units and remove column unit. this makes it easier to calculate
        # the numbers for the canton
        waste_df = waste_df[
            (waste_df["jahr"] >= FIRST_YEAR) & (waste_df["einheit"] == "Tonnen")
        ]
        waste_df = waste_df[waste_df["kategorie"] != "Kunststoffe"]
        waste_df.drop(columns=["einheit"], inplace=True)
        waste_df = waste_df.rename(columns={"wert": "menge_t"})
        # add total for canton
        group_fields = ["jahr", "kategorie"]
        grouped = (
            waste_df[group_fields + ["menge_t"]].groupby(group_fields).sum().reset_index()
        )
        grouped["bfs_gemeindenummer"] = 0
        grouped["gemeinde"] = "Kanton"
        waste_df = pd.concat([waste_df, grouped], ignore_index=True)

        pop_df = pd.read_csv(SOURCE_BEV_URL, sep=";")
        pop_df = pop_df[["jahr", "gemeinde", "endbestand", "anfangsbestand"]]
        pop_df["mittl_bestand"] = (pop_df["endbestand"] + pop_df["anfangsbestand"]) / 2
        pop_df = pop_df[pop_df["jahr"] >= FIRST_YEAR]
        # add total for canton
        group_fields = ["jahr"]
        grouped = (
            pop_df[["jahr", "endbestand", "anfangsbestand", "mittl_bestand"]]
            .groupby(["jahr"])
            .sum()
            .reset_index()
        )
        grouped["bfs_gemeindenummer"] = 0
        grouped["gemeinde"] = "Kanton"
        pop_df = pd.concat([pop_df, grouped], ignore_index=True)

        merged_df = waste_df.merge(
            pop_df, on=["gemeinde", "jahr"], how="left"
        ).reset_index()
        # calculate per capita kg consumption/production of waste
        merged_df["menge_kg_pro_kopf"] = (
            merged_df["menge_t"] / merged_df["mittl_bestand"] * 1000
        ).round(1)
        merged_df.to_parquet(LOCAL_DATA_WASTE, engine='pyarrow')
        pop_df.to_parquet(LOCAL_DATA_BEV, engine='pyarrow')
    return merged_df, pop_df


def show_intro(df):
    st.image(INTRO_IMAGE)
    cols = st.columns([1, 4, 1])
    with cols[1]:
        st.subheader(
            "Abfallmengen und Recycling in den Gemeinden des Kantons Basel-Landschaft"
        )
        st.markdown(text.INTRO)


def stat_commune(df):
    st.subheader("Abfallmengen und Recycling nach Gemeinde")
    filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorien": None}
    filter, filtered_df = get_filter(filter, df)
    pivot_df = filtered_df.pivot(
        index="gemeinde", columns=["kategorie"], values=[filter["einheit"]]
    ).reset_index()
    cols = [x[1] for x in pivot_df.columns]
    cols[0] = "gemeinde"
    pivot_df.columns = cols
    st.markdown(f"Einheit: {UNITS[filter['einheit']]}, Jahr: {filter['jahr']}")
    st.dataframe(pivot_df, hide_index=True)

    st.markdown("Statistik nach Abfall-Kategorie")
    group_fields = ["kategorie"]
    category_df = (
        filtered_df.groupby(group_fields)[filter["einheit"]]
        .agg(["min", "max", "mean", "sum"])
        .reset_index()
    )
    category_df.columns = ["Kategorie", "Minimum", "Maximum", "Mittelwert", "Total"]
    st.dataframe(category_df, hide_index=True)


def show_plots(df):
    plot_options = ["Balkendiagramm", "Histogramm", "Zeitserie"]
    plot = st.sidebar.selectbox(label="Grafik", options=plot_options)
    if plot_options.index(plot) == 0:
        # todo
        # show_mean = st.sidebar.checkbox("zeige Mittelwert als Linie")
        filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        # Remove kanton for absoute unit, as it overwhelms all other numbers
        if filter["einheit"] == "menge_t":
            filtered_df = filtered_df[filtered_df["gemeinde"] != "Kanton"]

        h = 2000 if filter["gemeinden"] == [] else 400 + 1800 / 86 * len(filter["gemeinden"])
        settings = {
            "y": "gemeinde",
            "x": f"{filter['einheit']}:Q",
            "y_title": filter["kategorie"],
            "x_title": UNITS[filter["einheit"]],
            "tooltip": ["jahr", "gemeinde", filter["einheit"]],
            "width": 600,
            "height": h,
            "title": f"Balkendiagramm ({filter['kategorie']})",
        }
        # todo vertical line
        # if show_mean:
        #     mean = filtered_df[filtered_df[filter["einheit"]] > 0][filter["einheit"]].mean()
        #     filtered_df["mittelwert"] = mean
        #     settings["h_line"] = "mittelwert"
        plots.barchart(filtered_df, settings)
    elif plot_options.index(plot) == 1:
        filter = {"jahr": None, "einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        # Remove kanton for absoute unit, as it overwhelms all other numbers
        if filter["einheit"] == "menge_t":
            filtered_df = filtered_df[filtered_df["gemeinde"] != "Kanton"]
        settings = {
            "x": f"{filter['einheit']}:Q",
            "y": "count()",
            "x_title": UNITS[filter["einheit"]],
            "y_title": "Anzahl Gemeinden",
            "tooltip": ["jahr", "gemeinde", filter["einheit"]],
            "width": 800,
            "height": 400,
            "title": f"Histogramm ({filter['kategorie']})",
        }
        plots.histogram(filtered_df, settings)
    elif plot_options.index(plot) == 2:
        filter = {"einheit": None, "gemeinden": [], "kategorie": None}
        filter, filtered_df = get_filter(filter, df)
        # Remove kanton for absoute unit, as it overwhelms all other numbers
        if (filter["einheit"] == "menge_t") & (filter["gemeinden"] == []):
            filtered_df = filtered_df[filtered_df["gemeinde"] != "Kanton"]
        settings = {
            "x": "jahr",
            "x_dt": "N",
            "color": "gemeinde",
            "y": filter["einheit"],
            "y_dt": "Q",
            "x_title": filter["kategorie"],
            "y_title": UNITS[filter["einheit"]],
            "tooltip": ["jahr", "gemeinde", filter["einheit"]],
            "width": 800,
            "height": 600,
            "title": f"Zeitserie ({filter['kategorie']})",
        }
        plots.line_chart(filtered_df, settings)


def get_total_df(_df, einheit, gemeinde):
    if gemeinde is not None:
        _df = _df[_df["gemeinde"] == gemeinde]
        _df = _df[["jahr", einheit]]
        result = _df.groupby("jahr").sum().reset_index()
    else:
        _df = _df[_df["gemeinde"] != "Kanton"]
        _df = _df[["gemeinde", "jahr", einheit]]
        result = _df.groupby(["gemeinde", "jahr"]).sum().reset_index()
    return result


def get_gemeinde_rank(df, einheit, gemeinde):
    df["rang"] = df[einheit].rank(ascending=False)
    return df[df["gemeinde"] == gemeinde].iloc[0]["rang"]


def get_general_text(df, gemeinde):
    einheit = "menge_t"
    total_gemeinde_t_df = get_total_df(df, einheit, gemeinde)
    first_year_waste_t = (
        total_gemeinde_t_df[(total_gemeinde_t_df["jahr"] == YEARS[0])]
        .iloc[0][einheit]
        .round(0)
    )
    last_year_waste_t = (
        total_gemeinde_t_df[(total_gemeinde_t_df["jahr"] == YEARS[-1])]
        .iloc[0][einheit]
        .round(0)
    )
    qualifier_diff_t = "mehr" if last_year_waste_t > first_year_waste_t else "weniger"

    einheit = "menge_kg_pro_kopf"
    total_gemeinde_kg_df = get_total_df(df, einheit, gemeinde)

    first_year_waste_kg = (
        total_gemeinde_kg_df[(total_gemeinde_kg_df["jahr"] == YEARS[0])]
        .iloc[0][einheit]
        .round(0)
    )
    last_year_waste_kg = (
        total_gemeinde_kg_df[(total_gemeinde_kg_df["jahr"] == YEARS[-1])]
        .iloc[0][einheit]
        .round(0)
    )
    qualifier_diff_kg = "stieg" if last_year_waste_kg > first_year_waste_kg else "sank"
    increase_pct = abs(first_year_waste_t - last_year_waste_t) / first_year_waste_t
    rank_basis_df = get_total_df(df, einheit, None)
    rank_basis_df = rank_basis_df[rank_basis_df["jahr"] == YEARS[-1]]
    rank = get_gemeinde_rank(rank_basis_df, einheit, gemeinde)
    text = f"""**Abfall total**: Die Gemeinde {gemeinde} hat im Jahr {YEARS[-1]} insgesamt {last_year_waste_t: .1f} Tonnen Abfall 
    produziert, {abs(last_year_waste_t - first_year_waste_t)} Tonnen {qualifier_diff_t} als in {YEARS[0]}. Die pro Kopf Produktion {qualifier_diff_kg}
    von {first_year_waste_kg} kg/Kopf in {YEARS[0]} auf {last_year_waste_kg} kg/Kopf in {YEARS[-1]} ({increase_pct * 100: .1f}%). Unter den Gemeinden des Kantons Basel-Landschaft belegt 
    {gemeinde} beim Total des Abfalls in {YEARS[-1]} Rang {rank:.0f} von {rank_basis_df['rang'].max():.0f}.
    """
    return text


def get_category_text(df, kategorie, gemeinde):
    df["rank_kg"] = df["menge_kg_pro_kopf"].rank(ascending=False)
    df["rank_t"] = df["menge_t"].rank(ascending=False)
    generate_expr = "produziert" if kategorie == KEHRICHT else "gerecycelt"

    first_year_t = df[(df["jahr"] == YEARS[0]) & (df["gemeinde"] == gemeinde)].iloc[0][
        "menge_t"
    ]
    last_year_t = df[(df["jahr"] == YEARS[-1]) & (df["gemeinde"] == gemeinde)].iloc[0][
        "menge_t"
    ]

    first_year_kg = df[(df["jahr"] == YEARS[0]) & (df["gemeinde"] == gemeinde)].iloc[0][
        "menge_kg_pro_kopf"
    ]
    last_year_kg = df[(df["jahr"] == YEARS[-1]) & (df["gemeinde"] == gemeinde)].iloc[0][
        "menge_kg_pro_kopf"
    ]
    rank_basis_df = get_total_df(df, "menge_kg_pro_kopf", None)
    rank_basis_df = rank_basis_df[rank_basis_df["jahr"] == YEARS[-1]]
    rank = get_gemeinde_rank(rank_basis_df, "menge_kg_pro_kopf", gemeinde)
    if last_year_t > 0:
        text = f"""**{kategorie}**: Es wurden in {YEARS[-1]} in {gemeinde} {last_year_t: .1f} Tonnen {kategorie} {generate_expr}, dies entspricht
        {last_year_kg: .1f} kg/Kopf. Im {YEARS[0]} waren es {first_year_t: .1f} Tonnen und {first_year_kg: .1f} kg/Kopf. Im Ranking der Gemeinden erreicht {gemeinde} bei der pro-Kopf Produktion 
        von {kategorie} Platz {rank: .0f}.
        """
    else:
        text = ""
    return text


def show_commune_report(waste_df, pop_df):
    options_gemeinden = sorted(list(pop_df["gemeinde"].unique()))
    options_gemeinden.remove('Kanton')
    options_kategorie = sorted(list(waste_df["kategorie"].unique()))
    gemeinde = st.sidebar.selectbox("Gemeinde", options=options_gemeinden)
    einwohner = pop_df[
        (pop_df["jahr"] == YEARS[-1]) & (pop_df["gemeinde"] == gemeinde)
    ].iloc[0]["mittl_bestand"]
    st.subheader(
        f"Zusammenfassung Gemeinde {gemeinde} (Einwohner in {YEARS[-1]}: {einwohner: .0f})"
    )

    text = get_general_text(waste_df, gemeinde)
    st.markdown(text)
    for kategorie in options_kategorie:
        df_filtered = waste_df[waste_df["kategorie"] == kategorie]
        text = get_category_text(df_filtered, kategorie, gemeinde)
        if text > "":
            st.markdown(text)


def main():
    """
    main menu with 3 options: cum consumption year of day, mean daily consumption in week
    and mean 1/4 consumption in day for selected period and years
    """
    init()
    waste_df, pop_df = get_data()
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
        show_intro(waste_df)
    elif menu_action == menu_options[1]:
        stat_commune(waste_df)
    elif menu_action == menu_options[2]:
        show_plots(waste_df)
    elif menu_action == menu_options[3]:
        show_commune_report(waste_df, pop_df)

    st.sidebar.markdown(get_show_intro(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
