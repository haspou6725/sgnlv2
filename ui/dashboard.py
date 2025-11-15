"""
SGNL-V2 Streamlit Dashboard
Real-time monitoring and signal visualization
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import get_sqlite_cache

# Page config
st.set_page_config(
    page_title="SGNL-V2 Dashboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    h1 {
        color: #1f77b4;
    }
    .signal-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize cache
@st.cache_resource
def get_cache():
    return get_sqlite_cache()

cache = get_cache()

# Header
st.title("🔥 SGNL-V2 Dashboard")
st.markdown("**Real-time Short-Scalp Signal Monitor**")

# Sidebar
st.sidebar.header("⚙️ Settings")
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 30, 5)
min_score_filter = st.sidebar.slider("Minimum Score Filter", 0, 100, 70)

# Auto refresh
if auto_refresh:
    placeholder = st.empty()
    time.sleep(0.1)

# Main content
col1, col2, col3, col4 = st.columns(4)

# Get data
try:
    scores = cache.get_scores()
    signals = cache.get_last_signals(limit=50)
    
    # Calculate metrics
    active_symbols = len(scores)
    recent_signals = len([s for s in signals if datetime.now().timestamp() - s.get('timestamp', 0) < 3600])
    avg_score = sum([s.get('score', 0) for s in scores]) / len(scores) if scores else 0
    high_score_count = len([s for s in scores if s.get('score', 0) >= min_score_filter])
    
    with col1:
        st.metric("Active Symbols", active_symbols, delta=None)
    
    with col2:
        st.metric("Signals (1h)", recent_signals, delta=None)
    
    with col3:
        st.metric("Avg Score", f"{avg_score:.1f}", delta=None)
    
    with col4:
        st.metric(f"Score ≥ {min_score_filter}", high_score_count, delta=None)
    
    st.markdown("---")
    
    # Two columns layout
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.subheader("📊 Top Scoring Symbols")
        
        if scores:
            # Filter and sort
            filtered_scores = [s for s in scores if s.get('score', 0) >= min_score_filter]
            sorted_scores = sorted(filtered_scores, key=lambda x: x.get('score', 0), reverse=True)[:20]
            
            if sorted_scores:
                # Create dataframe
                df_scores = pd.DataFrame([{
                    "Symbol": s.get('symbol', 'N/A'),
                    "Score": f"{s.get('score', 0):.1f}",
                    "Features": s.get('features', '{}'),
                    "Updated": datetime.fromtimestamp(s.get('timestamp', 0)).strftime("%H:%M:%S")
                } for s in sorted_scores])
                
                st.dataframe(
                    df_scores,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # Score distribution chart
                st.subheader("📈 Score Distribution")
                fig = px.histogram(
                    [s.get('score', 0) for s in scores],
                    nbins=20,
                    labels={'value': 'Score', 'count': 'Frequency'},
                    title="Symbol Score Distribution"
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No symbols with score ≥ {min_score_filter}")
        else:
            st.info("No scoring data available yet. Engine may be starting up...")
    
    with right_col:
        st.subheader("🔔 Recent Signals")
        
        if signals:
            # Show last 10 signals
            for signal in signals[:10]:
                symbol = signal.get('symbol', 'N/A')
                entry = signal.get('entry', 0)
                tp = signal.get('tp', 0)
                sl = signal.get('sl', 0)
                score = signal.get('score', 0)
                timestamp = signal.get('timestamp', 0)
                
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                
                # Calculate percentages
                tp_pct = ((entry - tp) / entry * 100) if entry > 0 else 0
                sl_pct = ((sl - entry) / entry * 100) if entry > 0 else 0
                
                st.markdown(f"""
                <div class="signal-card">
                    <strong>{symbol}</strong> - Score: {score:.1f}/100<br>
                    Entry: ${entry:.8f}<br>
                    TP: ${tp:.8f} (+{tp_pct:.2f}%)<br>
                    SL: ${sl:.8f} (-{sl_pct:.2f}%)<br>
                    <small>🕐 {time_str}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No signals generated yet")
    
    # Bottom section
    st.markdown("---")
    
    # Feature breakdown for top symbol
    if scores and sorted_scores:
        st.subheader("🔍 Top Symbol Analysis")
        
        top_symbol = sorted_scores[0]
        symbol = top_symbol.get('symbol', 'N/A')
        score = top_symbol.get('score', 0)
        
        st.markdown(f"**{symbol}** - Score: **{score:.1f}/100**")
        
        # Try to parse features
        import json
        features_str = top_symbol.get('features', '{}')
        try:
            features = json.loads(features_str) if isinstance(features_str, str) else features_str
            
            # Display features
            feat_col1, feat_col2, feat_col3 = st.columns(3)
            
            with feat_col1:
                st.metric("Ask Dominance", f"{features.get('ask_dominance', 0):.1f}%")
                st.metric("OBI", f"{features.get('orderbook_imbalance', 0):.1f}")
                st.metric("Sweep", "✅" if features.get('sweep_detected', False) else "❌")
            
            with feat_col2:
                st.metric("Sell Wall", f"{features.get('sell_wall_pressure', 0):.1f}")
                st.metric("Buy Exhaustion", f"{features.get('buy_wall_exhaustion', 0):.1f}")
                st.metric("OI Divergence", f"{features.get('oi_divergence', 0):.1f}")
            
            with feat_col3:
                st.metric("Funding Pressure", f"{features.get('funding_pressure', 0):.1f}")
                st.metric("Micro Momentum", f"{features.get('micro_momentum', 0):.1f}")
                st.metric("VWAP Distance", f"{features.get('vwap_distance', 0):.4f}%")
        except Exception as e:
            st.warning(f"Could not parse features: {e}")
    
    # Status footer
    st.markdown("---")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {current_time} | Auto-refresh: {'ON' if auto_refresh else 'OFF'}")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the SGNL-V2 engine is running and generating data.")
