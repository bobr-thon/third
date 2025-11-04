import streamlit as st
import pandas as pd
import altair as alt

# === PAGE CONFIG ===
st.set_page_config(page_title="Skin Profit Dashboard", layout="wide")
st.title("💰 Skin Profit Dashboard")

# === SIDEBAR ===
st.sidebar.header("⚙️ Re-investment Mode")
reinvestment_mode = st.sidebar.checkbox("Enable Re-investment Mode", value=False)
st.sidebar.markdown(
    "<small>Profit from each skin is reinvested sequentially. Leftover money is tracked.</small>",
    unsafe_allow_html=True
)

st.sidebar.header("📝 Custom Skin Names")
enable_custom_names = st.sidebar.checkbox("Enable Custom Names", value=False)

st.sidebar.header("📊 Chart Display Mode")
chart_focus_mode = st.sidebar.checkbox("Enable Chart Focus Mode (show only selected chart)", value=False)
if chart_focus_mode:
    chart_focus = st.sidebar.radio(
        "Select chart to display:",
        ("Profit per Skin", "ROI % per Skin", "Portfolio Growth"),
        index=0
    )

st.sidebar.header("🔧 What-if Scenario")
sell_modifier = st.sidebar.slider("Adjust Sell Prices (%)", -50.0, 50.0, 0.0, 1.0)
fee_modifier = st.sidebar.slider("Adjust Marketplace Fees (%)", -10.0, 10.0, 0.0, 0.1)

# === INPUT ===
num_skins = st.number_input("Enter number of skins:", min_value=1, value=2, step=1)

skin_data = []
st.markdown("---")
input_col, display_col = st.columns([1, 2])

with input_col:
    st.subheader("📝 Input Skins")

    reinvestment_funds = None

    for i in range(1, num_skins + 1):
        key_buy = f"buy{i}"
        key_sell = f"sell{i}"
        key_fee = f"fee{i}"
        key_name = f"name{i}"
        key_expander = f"expander_{i}"

        if key_expander not in st.session_state:
            st.session_state[key_expander] = True

        skin_label = f"Skin {i}"
        if enable_custom_names:
            custom_name = st.session_state.get(key_name, f"Skin {i}")
            skin_label += f" ({custom_name})"
        else:
            custom_name = f"Skin {i}"

        buy_prev = st.session_state.get(key_buy)
        sell_prev = st.session_state.get(key_sell)
        fee_prev = st.session_state.get(key_fee)

        with st.expander(skin_label, expanded=st.session_state[key_expander]):
            # Handle reinvestment auto buy
            if reinvestment_mode and i > 1 and reinvestment_funds is not None:
                buy_price = reinvestment_funds
                st.number_input("Buy Price (Auto)", min_value=0.0, value=float(buy_price), step=1.0, key=key_buy, disabled=True)
            else:
                buy_price = st.number_input("Buy Price", min_value=0.0, value=100.0, step=1.0, key=key_buy)

            sell_price = st.number_input("Sell Price", min_value=0.0, value=150.0, step=1.0, key=key_sell)
            fee = st.number_input("Marketplace Fee %", min_value=0.0, max_value=100.0, value=8.0, step=0.1, key=key_fee)
            if enable_custom_names:
                custom_name = st.text_input("Custom Name", value=custom_name, key=key_name)

        if (buy_prev and buy_prev != buy_price) or (sell_prev and sell_prev != sell_price) or (fee_prev and fee_prev != fee):
            st.session_state[key_expander] = False

        # Apply modifiers
        sell_price_adj = sell_price * (1 + sell_modifier / 100)
        fee_adj = max(fee + fee_modifier, 0)
        net = max(sell_price_adj * (1 - fee_adj / 100), 0)
        profit = net - buy_price
        roi = (profit / buy_price * 100) if buy_price > 0 else 0

        # Store reinvestment amount for next iteration
        reinvestment_funds = net if reinvestment_mode else None

        skin_data.append({
            "Skin": custom_name,
            "Skin Num": i,
            "Buy Price": buy_price,
            "Sell Price": sell_price_adj,
            "Fee %": fee_adj,
            "Net Received": net,
            "Profit": profit,
            "ROI %": roi
        })

# === DATAFRAME ===
df = pd.DataFrame(skin_data)

# === PORTFOLIO CALCULATION ===
df["Cumulative Money"] = df["Profit"].cumsum() + df["Buy Price"].iloc[0]

# === TOTALS ===
total_money_received = df["Net Received"].sum()
initial_investment = df["Buy Price"].sum()
total_profit = total_money_received - initial_investment
total_roi = (total_profit / initial_investment * 100) if initial_investment > 0 else 0

# === METRICS ===
st.subheader("🏆 Total Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Money Received", f"${total_money_received:.2f}")
col2.metric("Total Profit", f"${total_profit:.2f}")
col3.metric("Total ROI", f"{total_roi:.2f}%")

st.markdown("---")

# === DISPLAY ===
with display_col:
    st.subheader("📊 Individual Skin Results")
    df.index = range(1, len(df) + 1)
    df.index.name = "#"

    st.dataframe(
        df.style.format({
            "Buy Price": "${:.2f}",
            "Sell Price": "${:.2f}",
            "Net Received": "${:.2f}",
            "Profit": "${:.2f}",
            "ROI %": "{:.2f}%",
            "Cumulative Money": "${:.2f}"
        }).applymap(
            lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else
                      'color: red' if isinstance(x, (int, float)) and x < 0 else '',
            subset=["Profit"]
        )
    )

    # === CHARTS ===
    def make_profit_chart():
        return alt.Chart(df).mark_bar().encode(
            x='Skin',
            y='Profit',
            color=alt.condition(alt.datum.Profit > 0, alt.value("green"), alt.value("red")),
            tooltip=['Skin', 'Profit', 'ROI %']
        ).properties(width=600, height=300, title="Profit per Skin")

    def make_roi_chart():
        return alt.Chart(df).mark_line(point=True, interpolate="monotone").encode(
            x='Skin',
            y='ROI %',
            color=alt.value("blue"),
            tooltip=['Skin', 'ROI %']
        ).properties(width=600, height=300, title="ROI % per Skin")

    def make_portfolio_chart():
        return alt.Chart(df).mark_line(point=True, interpolate="monotone").encode(
            x='Skin Num:O',
            y='Cumulative Money:Q',
            color=alt.value("orange"),
            tooltip=["Skin", "Cumulative Money"]
        ).properties(width=600, height=300, title="Portfolio Growth Over Time")

    # === DISPLAY CHARTS ===
    if chart_focus_mode:
        if chart_focus == "Profit per Skin":
            st.altair_chart(make_profit_chart(), use_container_width=True)
        elif chart_focus == "ROI % per Skin":
            st.altair_chart(make_roi_chart(), use_container_width=True)
        else:
            st.altair_chart(make_portfolio_chart(), use_container_width=True)
    else:
        st.altair_chart(make_profit_chart(), use_container_width=True)
        st.altair_chart(make_roi_chart(), use_container_width=True)
        st.altair_chart(make_portfolio_chart(), use_container_width=True)

# === DOWNLOAD ===
st.subheader("💾 Export Data")
csv = df.to_csv(index=False)
st.download_button("Download Skin Data as CSV", csv, "skin_profit_data.csv", "text/csv")

st.markdown(
    """
    **Note:**  
    - Reinvestment mode auto-fills and locks buy prices based on previous net.  
    - Portfolio chart is now orange (smooth line).  
    - ROI chart is blue.  
    - All numbers rounded to 2 decimals.  
    """,
    unsafe_allow_html=True
)