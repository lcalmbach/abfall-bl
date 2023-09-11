# Waste Production Statistics & Visualization for Baselland Communes

This repository provides statistics and visualizations of waste production data from the communes of the Swiss canton of Baselland. 

## Data Sources
- **Waste Data**: Sourced from the OGD portal [data.bl.ch](https://data.bl.ch/), specifically [Abfallmengen nach Kategorie, Gemeinde und Jahr (seit 2017)](https://data.bl.ch/explore/dataset/12060/). The original data starts in 2017, however for many communes the year 2017 is incomplete, therefore the app only uses data starting in 2018.
- **Population Data**: Also sourced from [data.bl.ch](https://data.bl.ch/), from [Mittlere Wohnbevölkerung nach Nationalität, Gemeinde und Jahr (seit 1980)](https://data.bl.ch/explore/dataset/10080).

## Technology Stack
- **Application**: Written in Python, leveraging the web application framework [Streamlit](https://streamlit.io/).
- **Visualization**: All visualizations are crafted using [Altair](https://altair-viz.github.io/).

## Live Application
You can access the live application [here](https://abfall-bl.streamlit.app/).

## Getting Started

If you wish to fork or clone this repository and run the application locally, follow these steps (for a Windows environment):

```bash
git clone https://github.com/lcalmbach/abfall-bl.git
cd abfall-bl
py -m venv env
env\scripts\activate
pip install -r requirements.txt
streamlit run app.py
