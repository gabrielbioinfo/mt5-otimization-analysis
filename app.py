import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="UV | Análise de Estratégias MT5", layout="wide")
st.title("🔍 Análise Quantitativa de Estratégias - MetaTrader 5")

st.sidebar.header("📁 Upload do Arquivo XML")
xml_file = st.sidebar.file_uploader("Escolha o arquivo .xml exportado do Strategy Tester (MT5)", type="xml")

if not xml_file:
    if st.sidebar.button("🚀 Rodar Demo"):
        xml_file = "files/demo.xml"
        demo_trigger = True
    else:
        demo_trigger = False
else:
    demo_trigger = False

with open("files/demo.xml", "rb") as f:
    st.sidebar.download_button("📥 Baixar Exemplo XML", f, file_name="demo_mt5.xml")

st.sidebar.markdown("---")


@st.cache_data
def parse_mt5_xml(file_path):
    namespaces = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
    tree = ET.parse(file_path)
    root = tree.getroot()
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


if xml_file or demo_trigger:
    df_raw = parse_mt5_xml(xml_file)
    if not df_raw.shape[0] or not df_raw.shape[1]:
        st.error("⚠️ Nenhum dado encontrado no arquivo XML.")

    for col in ["Drawdown", "Expected Payoff", "Recovery Factor", "Sharpe Ratio"]:
        df_raw[col] = df_raw[col].str.replace("%", "", regex=False).str.replace(",", ".", regex=False)

    df_raw["Score"], df_raw["Classificação"] = zip(*df_raw.apply(pontuar_estrategia, axis=1))

    st.success(f"✅ {len(df_raw)} estratégias processadas com sucesso!")

    with st.sidebar.expander("🎛️ Filtros Avançados"):
        min_score = st.slider("Score mínimo", 0, 20, 10)
        max_drawdown = st.slider("Máximo Drawdown (%)", 0, 100, 20)
        min_sharpe = st.slider("Sharpe Ratio mínimo", 0.0, 3.0, 0.5, step=0.1)
        min_trades = st.slider("Mínimo de Trades", 0, 100, 10)

    df_filtered = df_raw[
        (df_raw["Score"] >= min_score)
        & (df_raw["Drawdown"].astype(float) <= max_drawdown)
        & (df_raw["Sharpe Ratio"].astype(float) >= min_sharpe)
        & (df_raw["Trades"].astype(int) >= min_trades)
    ]

    st.subheader("📊 Ranking das Estratégias Filtradas")
    st.dataframe(df_filtered.sort_values(by="Score", ascending=False).reset_index(drop=True))

    if not df_filtered.empty:
        top = df_filtered.sort_values(by="Score", ascending=False).iloc[0]

        st.subheader("📈 Radar das Top 3 Estratégias")
        st.markdown(
            "Esta análise mostra visualmente o equilíbrio entre as principais métricas das 3 estratégias com melhor pontuação. "
            "Permite comparar seus pontos fortes e entender por que cada uma se destaca."
        )

        top3 = df_filtered.sort_values(by="Score", ascending=False).head(3).copy()

        for i, row in top3.iterrows():
            st.markdown(
                f"### Estratégia {i + 1} - Score: **{row['Score']}** - Classificação: **{row['Classificação']}**"
            )
            st.markdown(
                f"**Resumo:** {row['Trades']} trades, Payoff Esperado: {row['Expected Payoff']}, "
                f"Drawdown: {row['Drawdown']}%, Sharpe: {row['Sharpe Ratio']}, Recovery: {row['Recovery Factor']}."
            )
            radar_data = pd.DataFrame(
                {
                    "Métrica": ["Trades", "Drawdown", "Recovery Factor", "Sharpe Ratio", "Expected Payoff"],
                    "Valor": [
                        int(row["Trades"]),
                        float(row["Drawdown"]),
                        float(row["Recovery Factor"]),
                        float(row["Sharpe Ratio"]),
                        float(row["Expected Payoff"]),
                    ],
                }
            )
            fig = px.line_polar(
                radar_data, r="Valor", theta="Métrica", line_close=True, title=f"Radar Estratégia {i + 1}"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(top3.reset_index(drop=True), use_container_width=True)

        st.subheader("📌 Comparador de Estratégias")
        st.markdown(
            "Compare rapidamente o desempenho de múltiplas estratégias selecionadas com base em métricas chave. Ideal para identificar opções alternativas de alta qualidade."
        )
        selected_rows = st.multiselect(
            "Selecione estratégias para comparar (por índice)",
            df_filtered.index.tolist(),
            default=df_filtered.index[:3].tolist(),
        )
        if selected_rows:
            df_selected = df_filtered.loc[selected_rows]
            fig_compare = px.bar(
                df_selected,
                x=df_selected.index.astype(str),
                y="Score",
                color="Classificação",
                hover_data=["Trades", "Drawdown", "Sharpe Ratio", "Expected Payoff"],
                title="Comparação de Estratégias Selecionadas",
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        st.subheader("📊 Impacto dos Parâmetros nas Métricas")
        st.markdown(
            "Esta seção analisa como os parâmetros otimizados afetam diretamente a pontuação geral (Score). Útil para entender a sensibilidade da estratégia."
        )
        parametros = [
            col for col in df_filtered.columns if col.lower().endswith("period") or col.lower().startswith("rsi")
        ]
        if parametros:
            param_to_plot = st.selectbox("Escolha um parâmetro para análise", parametros)
            if param_to_plot:
                df_filtered[param_to_plot] = pd.to_numeric(df_filtered[param_to_plot], errors="coerce")
                fig_param = px.scatter(
                    df_filtered,
                    x=param_to_plot,
                    y="Score",
                    color="Classificação",
                    hover_data=["Trades", "Drawdown", "Sharpe Ratio"],
                    title=f"Score vs {param_to_plot}",
                )
                st.plotly_chart(fig_param, use_container_width=True)

        st.subheader("🧪 Validação Out-of-Sample (por Pass)")
        st.markdown(
            "Avalia se as estratégias performam bem fora da amostra usada na otimização, dividindo por número de `Pass` (tentativas ou execuções)."
        )
        if "Pass" in df_filtered.columns:
            df_filtered["Pass"] = pd.to_numeric(df_filtered["Pass"], errors="coerce")
            threshold_pass = df_filtered["Pass"].median()
            oos_set = df_filtered[df_filtered["Pass"] > threshold_pass]
            is_set = df_filtered[df_filtered["Pass"] <= threshold_pass]
            st.markdown(f"**In-Sample:** {len(is_set)} | **Out-of-Sample:** {len(oos_set)}")
            fig_oos = px.box(
                df_filtered,
                x=["IS" if p <= threshold_pass else "OOS" for p in df_filtered["Pass"]],
                y="Score",
                title="Distribuição de Score: In-Sample vs Out-of-Sample",
            )
            st.plotly_chart(fig_oos, use_container_width=True)

        st.subheader("🔥 Heatmap de Parâmetros")
        st.markdown(
            "Visualiza como pares de parâmetros influenciam o Score. Zonas quentes indicam combinações mais robustas e promissoras."
        )
        if len(parametros) >= 2:
            p1, p2 = parametros[:2]
            df_filtered[p1] = pd.to_numeric(df_filtered[p1], errors="coerce")
            df_filtered[p2] = pd.to_numeric(df_filtered[p2], errors="coerce")
            heatmap_data = df_filtered.pivot_table(index=p2, columns=p1, values="Score", aggfunc="mean")
            st.write("Média de Score por Par de Parâmetros")
            st.dataframe(heatmap_data)
            fig_heat = px.imshow(heatmap_data, text_auto=True, aspect="auto", title=f"Heatmap: {p1} x {p2}")
            st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("📉 Curva de Score ao longo do Pass")
        st.markdown(
            "Mostra a tendência de Score ao longo da ordem dos testes (Pass). Pode indicar overfitting ou estabilidade do desempenho."
        )
        if "Pass" in df_filtered.columns:
            df_filtered["Pass"] = pd.to_numeric(df_filtered["Pass"], errors="coerce")
            fig_curve = px.line(
                df_filtered.sort_values("Pass"), x="Pass", y="Score", title="Evolução do Score ao Longo do Pass"
            )
            st.plotly_chart(fig_curve, use_container_width=True)

        st.subheader("🔗 Correlação entre Métricas")
        st.markdown(
            "Mede como as principais métricas se relacionam entre si. Correlações positivas ou negativas ajudam a entender trade-offs."
        )
        numeric_cols = ["Score", "Expected Payoff", "Drawdown", "Sharpe Ratio", "Recovery Factor"]
        for col in numeric_cols:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce")
        corr = df_filtered[numeric_cols].corr()
        st.dataframe(corr)
        fig_corr = px.imshow(corr, text_auto=True, aspect="auto", title="Correlação entre Métricas")
        st.plotly_chart(fig_corr, use_container_width=True)

        st.subheader("🎯 Dispersão Score vs Expected Payoff")
        st.markdown(
            "Mostra a relação entre payoff esperado e Score, com tamanho dos pontos representando o número de trades. Ideal para buscar estratégias com boa relação risco-retorno."
        )
        df_filtered["Expected Payoff"] = pd.to_numeric(df_filtered["Expected Payoff"], errors="coerce")
        df_filtered["Trades"] = pd.to_numeric(df_filtered["Trades"], errors="coerce")
        fig_scatter = px.scatter(
            df_filtered,
            x="Expected Payoff",
            y="Score",
            size="Trades",
            color="Classificação",
            hover_data=["Drawdown", "Sharpe Ratio"],
            title="Score vs Expected Payoff",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.download_button(
        "📥 Baixar resultados como CSV",
        data=df_filtered.to_csv(index=False),
        file_name="estrategias_filtradas.csv",
        mime="text/csv",
    )

else:
    st.info("Faça o upload de um arquivo de otimização do MT5 em XML para iniciar a análise.")
