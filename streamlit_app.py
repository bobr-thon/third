import streamlit as st
import pandas as pd
import altair as alt

# === PAGE CONFIG ===
st.set_page_config(page_title="Skin Profit Dashboard - Pro Edition", layout="wide")
st.title("💰 Skin Profit Dashboard - Pro Edition")

# === SIDEBAR ===
st.sidebar.header("⚙️ Re-investment Mode")
reinvestment_mode = st.sidebar.checkbox("Enable Re-investment Mode", value=False)
st.sidebar.markdown(
    "<small>Profit from each skin is reinvested sequentially. Subsequent buy prices are auto-filled.</small>",
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

# === TABS ===
tab_basic, tab_advanced = st.tabs(["Basic Dashboard", "Advanced Data"])

# === SKIN INPUT FUNCTION ===
def skin_input_row(i, reinvestment_funds=None, tab_prefix="basic"):
    key_buy = f"{tab_prefix}_buy{i}"
    key_sell = f"{tab_prefix}_sell{i}"
    key_fee = f"{tab_prefix}_fee{i}"
    key_name = f"{tab_prefix}_name{i}"
    key_expander = f"{tab_prefix}_expander_{i}"

    if key_expander not in st.session_state:
        st.session_state[key_expander] = True

    skin_label = f"Skin {i}"
    custom_name = st.session_state.get(key_name, f"Skin {i}")
    if enable_custom_names:
        skin_label += f" ({custom_name})"

    buy_prev = st.session_state.get(key_buy)
    sell_prev = st.session_state.get(key_sell)
    fee_prev = st.session_state.get(key_fee)

    with st.expander(skin_label, expanded=st.session_state[key_expander]):
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

    sell_price_adj = sell_price * (1 + sell_modifier / 100)
    fee_adj = max(fee + fee_modifier, 0)
    net = max(sell_price_adj * (1 - fee_adj / 100), 0)
    profit = net - buy_price
    roi = (profit / buy_price * 100) if buy_price > 0 else 0

    return {
        "Skin": custom_name,
        "Skin Num": i,
        "Buy Price": buy_price,
        "Sell Price": sell_price_adj,
        "Fee %": fee_adj,
        "Net Received": net,
        "Profit": profit,
        "ROI %": roi
    }, net

# === CHART FUNCTIONS ===
def make_profit_chart(df):
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("Skin:O", title="Skin"),  # categorical
        y=alt.Y("Profit:Q", title="Profit"),
        color=alt.condition(alt.datum.Profit>0, alt.value("green"), alt.value("red")),
        tooltip=['Skin','Profit','ROI %']
    ).properties(width=600,height=300,title="Profit per Skin")

def make_roi_chart(df):
    return alt.Chart(df).mark_line(point=True, interpolate="monotone").encode(
        x=alt.X("Skin Num:O", title="Skin Num"),  # ordinal for line
        y=alt.Y("ROI %:Q", title="ROI %"),
        color=alt.value("blue"),
        tooltip=['Skin','ROI %']
    ).properties(width=600,height=300,title="ROI % per Skin")

def make_portfolio_chart(df):
    return alt.Chart(df).mark_line(point=True, interpolate="monotone").encode(
        x=alt.X("Skin Num:O", title="Skin Num"),
        y=alt.Y("Cumulative Money:Q", title="Cumulative Money"),
        color=alt.value("orange"),
        tooltip=["Skin","Cumulative Money"]
    ).properties(width=600,height=300,title="Portfolio Growth Over Time")

# === BASIC TAB ===
with tab_basic:
    num_skins = st.number_input("Enter number of skins:", min_value=1, value=2, step=1)
    skin_data = []
    reinvestment_funds = None
    input_col, display_col = st.columns([1,2])

    with input_col:
        for i in range(1, num_skins + 1):
            skin_row, reinvestment_funds = skin_input_row(i, reinvestment_funds, tab_prefix="basic")
            skin_data.append(skin_row)

    df_basic = pd.DataFrame(skin_data)
    df_basic["Cumulative Money"] = df_basic["Profit"].cumsum() + df_basic["Buy Price"].iloc[0]

    # Totals
    total_invested = df_basic["Buy Price"].sum()
    total_money_received = df_basic["Net Received"].sum()
    total_profit = total_money_received - total_invested
    total_roi = (total_profit / total_invested * 100) if total_invested > 0 else 0

    st.subheader("🏆 Total Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invested", f"${total_invested:.2f}")
    col2.metric("Total Money Received", f"${total_money_received:.2f}")
    col3.metric("Total Profit", f"${total_profit:.2f}")
    col4.metric("Total ROI", f"{total_roi:.2f}%")
    st.markdown("---")

    # Read-only table
    with display_col:
        st.subheader("📊 Individual Skin Results")
        df_basic.index = range(1, len(df_basic)+1)
        df_basic.index.name = "#"
        st.dataframe(df_basic, use_container_width=True)

        # Charts
        if chart_focus_mode:
            if chart_focus=="Profit per Skin": st.altair_chart(make_profit_chart(df_basic),use_container_width=True)
            elif chart_focus=="ROI % per Skin": st.altair_chart(make_roi_chart(df_basic),use_container_width=True)
            else: st.altair_chart(make_portfolio_chart(df_basic),use_container_width=True)
        else:
            st.altair_chart(make_profit_chart(df_basic),use_container_width=True)
            st.altair_chart(make_roi_chart(df_basic),use_container_width=True)
            st.altair_chart(make_portfolio_chart(df_basic),use_container_width=True)

# === ADVANCED TAB ===
with tab_advanced:
    st.subheader("📊 Individual Skin Results (Editable)")
    # Link to Basic tab data
    df_adv = df_basic.copy()
    df_adv.index = range(1, len(df_adv)+1)
    df_adv.index.name = "#"

    edited_df = st.data_editor(df_adv, num_rows="dynamic", use_container_width=True)
    edited_df["Net Received"] = edited_df["Sell Price"]*(1-edited_df["Fee %"]/100)
    edited_df["Profit"] = edited_df["Net Received"]-edited_df["Buy Price"]
    edited_df["ROI %"] = (edited_df["Profit"]/edited_df["Buy Price"]*100).fillna(0)
    edited_df["Cumulative Money"] = edited_df["Profit"].cumsum() + edited_df["Buy Price"].iloc[0]
    df_adv = edited_df

    # Performance Ranking
    st.subheader("🏅 Performance Ranking")
    ranking = df_adv.sort_values(by="Profit", ascending=False)[["Skin","Profit","ROI %"]]
    st.table(ranking)

    # Charts
    st.subheader("Profit Distribution")
    st.altair_chart(
        alt.Chart(df_adv).mark_bar().encode(
            x=alt.X("Profit:Q", bin=alt.Bin(maxbins=20)),
            y='count()',
            tooltip=['count()']
        ).properties(width=700,height=300),
        use_container_width=True
    )

    st.subheader("Cumulative ROI Over Time")
    df_adv["Cumulative ROI %"] = df_adv["ROI %"].cumsum()
    st.altair_chart(
        alt.Chart(df_adv).mark_line(point=True, interpolate="monotone").encode(
            x=alt.X("Skin Num:O"),
            y=alt.Y("Cumulative ROI %:Q"),
            color=alt.value("purple"),
            tooltip=["Skin","Cumulative ROI %"]
        ).properties(width=700,height=300),
        use_container_width=True
    )

    st.subheader("ROI vs Profit Scatter Plot")
    st.altair_chart(
        alt.Chart(df_adv).mark_circle(size=100).encode(
            x='Profit:Q', y='ROI %:Q',
            color=alt.value("teal"),
            tooltip=["Skin","Profit","ROI %"]
        ).properties(width=700,height=300),
        use_container_width=True
    )
