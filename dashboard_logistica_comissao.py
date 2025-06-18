
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Dashboard Logística + Comissão", layout="wide")
st.title("📦 Dashboard de Vendas com Comissão e Logística")

# Função para exportar para PDF
def gerar_pdf(pedidos, resumo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Resumo de Indicadores", ln=True, align="C")
    pdf.ln(10)

    for titulo, valor in resumo.items():
        pdf.cell(200, 10, txt=f"{titulo}: R$ {valor:,.2f}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Resumo por Cliente", ln=True)
    pdf.ln(5)

    por_cliente = pedidos.groupby("Cliente")["Comissão (R$)"].sum().reset_index()
    for _, row in por_cliente.iterrows():
        pdf.cell(200, 10, txt=f"{row['Cliente']}: R$ {row['Comissão (R$)']:,.2f}", ln=True)

    output = BytesIO()
    pdf.output(output)
    return output

# Upload
arquivo = st.file_uploader("📁 Envie a planilha completa (.xlsx)", type=["xlsx"])
if arquivo:
    try:
        pedidos = pd.read_excel(arquivo, sheet_name="Pedidos")
        comissao = pd.read_excel(arquivo, sheet_name="Comissao")
        entregas = pd.read_excel(arquivo, sheet_name="Entregas")
        faixas = pd.read_excel(arquivo, sheet_name="Faixas_KM")

        # Pré-processamento
        pedidos = pedidos.merge(comissao, on="Categoria", how="left")
        pedidos["Comissão (R$)"] = pedidos["Valor Total"] * pedidos["Comissão (%)"]
        pedidos = pedidos.merge(entregas, on="PedidoID", how="left")
        pedidos["Data"] = pd.to_datetime(pedidos["Data"])

        def calcular_faixa(dist):
            for _, row in faixas.iterrows():
                if row["Raio Inicial"] <= dist <= row["Raio Final"]:
                    return row["Valor por KM"] * dist
            return 0.0

        pedidos["Custo Logístico"] = pedidos["Distância KM"].apply(lambda x: calcular_faixa(x))

        # Filtros
        with st.sidebar:
            st.header("🔎 Filtros")
            datas = st.date_input("Período", [])
            categoria = st.multiselect("Categoria", sorted(pedidos["Categoria"].unique()))
            cliente = st.multiselect("Cliente", sorted(pedidos["Cliente"].unique()))

        if datas:
            pedidos = pedidos[(pedidos["Data"] >= pd.to_datetime(datas[0])) & (pedidos["Data"] <= pd.to_datetime(datas[1]))]
        if categoria:
            pedidos = pedidos[pedidos["Categoria"].isin(categoria)]
        if cliente:
            pedidos = pedidos[pedidos["Cliente"].isin(cliente)]

        # Indicadores
        total_vendas = pedidos["Valor Total"].sum()
        total_comissao = pedidos["Comissão (R$)"].sum()
        total_logistica = pedidos["Custo Logístico"].sum()
        lucro_liquido = total_vendas - total_comissao - total_logistica

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Vendido", f"R$ {total_vendas:,.2f}")
        col2.metric("🎯 Comissão Total", f"R$ {total_comissao:,.2f}")
        col3.metric("🚚 Logística Total", f"R$ {total_logistica:,.2f}")
        col4.metric("📈 Lucro Estimado", f"R$ {lucro_liquido:,.2f}")

        st.markdown("---")

        # Gráfico de Vendas por Categoria (Pizza)
        st.subheader("🥧 Vendas por Categoria")
        graf_vendas = pedidos.groupby("Categoria")["Valor Total"].sum().reset_index()
        fig_vendas = px.pie(graf_vendas, names="Categoria", values="Valor Total", title="Vendas por Categoria", hole=0.4)
        fig_vendas.update_traces(textinfo='label+percent', hovertemplate="%{label}: R$ %{value:,.2f}")
        st.plotly_chart(fig_vendas, use_container_width=True)

        # Gráfico: Comissão por Categoria
        st.subheader("📊 Comissão por Categoria")
        graf_com_cat = pedidos.groupby("Categoria")["Comissão (R$)"].sum().reset_index()
        fig_com_cat = px.bar(graf_com_cat, x="Categoria", y="Comissão (R$)", text_auto=".2s", title="Comissão por Categoria")
        st.plotly_chart(fig_com_cat, use_container_width=True)

        # Gráfico: Comissão por Cliente
        st.subheader("📊 Comissão por Cliente")
        graf_com_cli = pedidos.groupby("Cliente")["Comissão (R$)"].sum().reset_index()
        fig_com_cli = px.bar(graf_com_cli, x="Cliente", y="Comissão (R$)", text_auto=".2s", title="Comissão por Cliente")
        st.plotly_chart(fig_com_cli, use_container_width=True)

        # Exportar PDF
        st.markdown("---")
        if st.button("📤 Baixar Resumo em PDF"):
            resumo = {
                "Total Vendido": total_vendas,
                "Comissão Total": total_comissao,
                "Logística Total": total_logistica,
                "Lucro Estimado": lucro_liquido
            }
            pdf_bytes = gerar_pdf(pedidos, resumo)
            st.download_button("📄 Clique aqui para baixar o PDF", data=pdf_bytes.getvalue(), file_name="resumo_dashboard.pdf")

    except Exception as e:
        st.error(f"Erro ao processar a planilha: {e}")
