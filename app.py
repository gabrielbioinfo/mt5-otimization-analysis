import xml.etree.ElementTree as ET

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="UV | Análise de Estratégias MT5", layout="wide")
st.title("🔍 Análise Quantitativa de Estratégias - MetaTrader 5")

st.sidebar.header("📁 Upload do Arquivo XML")
xml_file = st.sidebar.file_uploader("Escolha o arquivo .xml exportado do Strategy Tester (MT5)", type="xml")


@st.cache_data
def parse_mt5_xml(file_path):
    # Define o namespace usado pelo MT5
    namespaces = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}

    tree = ET.parse(file_path)
    root = tree.getroot()

    # Encontra as linhas da tabela
    rows = root.findall(".//ss:Row", namespaces=namespaces)
    parsed_rows = []

    for row in rows:
        cells = row.findall("ss:Cell", namespaces=namespaces)
        values = [
            (
                cell.find("ss:Data", namespaces=namespaces).text
                if cell.find("ss:Data", namespaces=namespaces) is not None
                else ""
            )
            for cell in cells
        ]
        parsed_rows.append(values)

    # Garante que há cabeçalho e pelo menos uma linha
    if len(parsed_rows) < 2:
        raise ValueError("O arquivo XML não contém dados suficientes para montar a tabela.")

    headers = parsed_rows[0]
    data = parsed_rows[1:]

    df = pd.DataFrame(data, columns=headers)

    df.rename(
        columns={
            "Equity DD %": "Drawdown",
            "Profit Factor": "Profit Factor",
            "Expected Payoff": "Expected Payoff",
            "Recovery Factor": "Recovery Factor",
            "Sharpe Ratio": "Sharpe Ratio",
            "Trades": "Trades",
        },
        inplace=True,
    )
    return df


def pontuar_estrategia(row):
    try:
        trades = int(row["Trades"])
        dd = float(row["Drawdown"])
        recovery = float(row["Recovery Factor"])
        sharpe = float(row["Sharpe Ratio"])
        payoff = float(row["Expected Payoff"])
    except:
        return 0, "Inválido"

    score = 0
    score += 0 if trades < 10 else 1 if trades < 31 else 2 if trades < 51 else 3 if trades < 101 else 4
    score += 0 if dd > 20 else 1 if dd > 15 else 2 if dd > 10 else 3 if dd > 5 else 4
    score += 0 if recovery < 1 else 1 if recovery < 1.5 else 2 if recovery < 2 else 3 if recovery < 3 else 4
    score += 0 if sharpe < 0.5 else 1 if sharpe < 1 else 2 if sharpe < 1.5 else 3 if sharpe < 2 else 4
    score += 0 if payoff < 5 else 1 if payoff < 10 else 2 if payoff < 25 else 3 if payoff < 50 else 4

    if score <= 6:
        categoria = "Fraca"
    elif score <= 12:
        categoria = "Regular"
    elif score <= 16:
        categoria = "Boa"
    else:
        categoria = "Excelente"

    return score, categoria


if xml_file:
    df_raw = parse_mt5_xml(xml_file)
    if not df_raw.shape[0] or not df_raw.shape[1]:
        st.error("⚠️ Nenhum dado encontrado no arquivo XML.")

    for col in ["Drawdown", "Expected Payoff", "Recovery Factor", "Sharpe Ratio"]:
        df_raw[col] = df_raw[col].str.replace("%", "", regex=False).str.replace(",", ".", regex=False)

    df_raw["Score"], df_raw["Classificação"] = zip(*df_raw.apply(pontuar_estrategia, axis=1))

    st.success(f"✅ {len(df_raw)} estratégias processadas com sucesso!")

    st.subheader("📊 Ranking das Estratégias")
    st.dataframe(df_raw.sort_values(by="Score", ascending=False).reset_index(drop=True))

    st.subheader("📈 Radar da Melhor Estratégia")
    top = df_raw.sort_values(by="Score", ascending=False).iloc[0]
    radar_data = pd.DataFrame(
        {
            "Métrica": ["Trades", "Drawdown", "Recovery Factor", "Sharpe Ratio", "Expected Payoff"],
            "Valor": [
                int(top["Trades"]),
                float(top["Drawdown"]),
                float(top["Recovery Factor"]),
                float(top["Sharpe Ratio"]),
                float(top["Expected Payoff"]),
            ],
        }
    )

    top_frame = top.to_frame()
    st.dataframe(top_frame, use_container_width=True)
    st.markdown("---")
    st.markdown(
        """
        O gráfico abaixo mostra as métricas da melhor estratégia em um gráfico radar. Quanto mais próximo do centro, pior a métrica.
        """
    )
    fig = px.line_polar(
        radar_data,
        r="Valor",
        theta="Métrica",
        line_close=True,
        title=f"Radar - Estratégia Top ({top['Classificação']})",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.download_button(
        "📥 Baixar resultados como CSV",
        data=df_raw.to_csv(index=False),
        file_name="estrategias_avaliadas.csv",
        mime="text/csv",
    )

else:
    st.info("Faça o upload de um arquivo de otimização do MT5 em XML para iniciar a análise.")
