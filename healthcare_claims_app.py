#!/usr/bin/env python3
"""
Healthcare Claims Analytics Dashboard
Interactive web application for claims analysis
Built with Streamlit
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import random

# Page configuration
st.set_page_config(
    page_title="Healthcare Claims Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding-top: 0rem;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Set random seed
np.random.seed(42)
random.seed(42)

# ============================================================================
# DATA GENERATION FUNCTIONS
# ============================================================================

@st.cache_data
def generate_claims_data():
    """Generate healthcare claims data"""
    
    # Define lookup data
    denial_reasons = [
        'Pre-authorization Required', 'Out of Network', 'Service Not Covered',
        'Duplicate Claim', 'Invalid Provider', 'Procedure Code Mismatch',
        'Patient Not Eligible', 'Exceeds Benefit Limit', 'Incomplete Documentation',
        'Age Restriction', 'Medical Necessity Not Met', 'Provider Contract Expired'
    ]
    
    procedure_codes = ['99213', '99214', '99215', '70553', '70554', '71020', 
                      '71046', '92004', '92012', '99203', '99204', '99205']
    
    states = ['CA', 'TX', 'NY', 'FL', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']
    
    provider_types = ['Hospital', 'Clinic', 'Specialist']
    plan_types = ['HMO', 'PPO', 'EPO']
    
    # Generate providers
    providers = pd.DataFrame({
        'provider_id': range(5001, 5151),
        'provider_name': [f'Medical Center {i}' for i in range(1, 151)],
        'provider_type': np.random.choice(provider_types, 150),
        'state': np.random.choice(states, 150),
        'network_status': np.random.choice(['In-Network', 'Out-of-Network'], 150, p=[0.8, 0.2]),
    })
    
    # Generate members
    members = pd.DataFrame({
        'member_id': range(1000001, 1010001),
        'member_name': [f'Member_{i}' for i in range(1, 10001)],
        'date_of_birth': [datetime(1950, 1, 1) + timedelta(days=random.randint(0, 20000)) 
                         for _ in range(10000)],
        'gender': np.random.choice(['M', 'F'], 10000),
        'plan_type': np.random.choice(plan_types, 10000, p=[0.4, 0.4, 0.2]),
        'state': np.random.choice(states, 10000),
    })
    
    # Generate claims
    claims = pd.DataFrame({
        'claim_id': range(3001, 3050001),
        'member_id': np.random.choice(members['member_id'].values, 50000),
        'provider_id': np.random.choice(providers['provider_id'].values, 50000),
        'claim_date': [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)) 
                      for _ in range(50000)],
        'service_date': [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)) 
                        for _ in range(50000)],
        'procedure_code': np.random.choice(procedure_codes, 50000),
        'billed_amount': np.random.uniform(100, 5000, 50000),
    })
    
    # Assign claim status
    claims['claim_status'] = claims.apply(
        lambda x: 'Approved' if random.random() < 0.75 else 
                 ('Denied' if random.random() < 0.8 else 'Pending'), axis=1
    )
    
    # Assign denial reason
    claims['denial_reason'] = claims['claim_status'].apply(
        lambda x: np.random.choice(denial_reasons) if x == 'Denied' else 'No Denial'
    )
    
    # Calculate amounts
    claims['allowed_amount'] = (claims['billed_amount'] * 
                               np.random.uniform(0.6, 0.95, 50000)).round(2)
    claims['paid_amount'] = claims.apply(
        lambda row: row['allowed_amount'] * 0.8 if row['claim_status'] == 'Approved' else 0, 
        axis=1
    ).round(2)
    
    claims['days_to_process'] = np.random.randint(5, 45, 50000)
    
    return providers, members, claims

# ============================================================================
# MAIN APP
# ============================================================================

# Title
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <h1>🏥 Healthcare Claims Analytics Platform</h1>
    <p style='font-size: 18px; color: #666;'>
        Interactive Dashboard for Claims Processing & Denial Analysis
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    generate_data = st.button("📊 Generate Sample Data", use_container_width=True)
    
    st.markdown("---")
    st.markdown("## 📋 Navigation")
    
    page = st.radio(
        "Select View:",
        ["📊 Dashboard", "📈 Analytics", "🔍 Detailed Analysis", "💰 Financial", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **Healthcare Claims Analytics**
    
    This dashboard provides comprehensive analysis of healthcare claims data including:
    - Approval metrics
    - Denial patterns
    - Provider performance
    - Geographic analysis
    """)

# Generate data on button click
if generate_data:
    st.session_state.data_generated = True

# Check if data is already generated
if 'data_generated' not in st.session_state:
    st.session_state.data_generated = False

# Generate data if needed
if st.session_state.data_generated:
    providers, members, claims = generate_claims_data()
    st.session_state.providers = providers
    st.session_state.members = members
    st.session_state.claims = claims
    st.success("✓ Data generated successfully! Select a view from the sidebar.")
    st.rerun()

# Check if data exists
if 'claims' not in st.session_state:
    st.warning("👈 Click 'Generate Sample Data' in the sidebar to get started!")
    st.stop()

providers = st.session_state.providers
members = st.session_state.members
claims = st.session_state.claims

# ============================================================================
# PAGE 1: DASHBOARD
# ============================================================================

if page == "📊 Dashboard":
    st.markdown("## 📊 Executive Dashboard")
    st.divider()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_claims = len(claims)
    approved_count = len(claims[claims['claim_status'] == 'Approved'])
    denied_count = len(claims[claims['claim_status'] == 'Denied'])
    approval_rate = (approved_count / total_claims * 100)
    
    with col1:
        st.metric(
            "Total Claims",
            f"{total_claims:,}",
            "Claims Processed"
        )
    
    with col2:
        st.metric(
            "Approval Rate",
            f"{approval_rate:.1f}%",
            delta=f"{approved_count:,} approved"
        )
    
    with col3:
        st.metric(
            "Denial Rate",
            f"{100-approval_rate:.1f}%",
            delta=f"{denied_count:,} denied"
        )
    
    with col4:
        total_paid = claims['paid_amount'].sum()
        st.metric(
            "Total Paid",
            f"${total_paid/1e6:.1f}M",
            "To Providers"
        )
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Claims Status Distribution")
        status_data = claims['claim_status'].value_counts()
        fig_status = px.pie(
            values=status_data.values,
            names=status_data.index,
            colors=['#2ecc71', '#e74c3c', '#f39c12'],
            hole=0.3
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        st.markdown("### Financial Summary")
        financial_data = pd.DataFrame({
            'Category': ['Billed', 'Allowed', 'Paid'],
            'Amount': [
                claims['billed_amount'].sum(),
                claims['allowed_amount'].sum(),
                claims['paid_amount'].sum()
            ]
        })
        fig_financial = px.bar(
            financial_data,
            x='Category',
            y='Amount',
            color='Category',
            color_discrete_sequence=['#3498db', '#2ecc71', '#f39c12']
        )
        st.plotly_chart(fig_financial, use_container_width=True)
    
    st.divider()
    
    # Additional metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Processing Time")
        avg_time = claims['days_to_process'].mean()
        median_time = claims['days_to_process'].median()
        
        st.info(f"""
        **Average Processing:** {avg_time:.1f} days
        
        **Median:** {median_time:.0f} days
        
        **Range:** {claims['days_to_process'].min()}-{claims['days_to_process'].max()} days
        """)
    
    with col2:
        st.markdown("### Claims by Status")
        status_summary = pd.DataFrame({
            'Status': status_data.index,
            'Count': status_data.values,
            'Percentage': (status_data.values / total_claims * 100).round(1)
        })
        st.dataframe(status_summary, hide_index=True, use_container_width=True)

# ============================================================================
# PAGE 2: ANALYTICS
# ============================================================================

elif page == "📈 Analytics":
    st.markdown("## 📈 Detailed Analytics")
    st.divider()
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["Denial Reasons", "Providers", "Geographic", "Trends"])
    
    with tab1:
        st.markdown("### Top Denial Reasons")
        
        denied_claims = claims[claims['claim_status'] == 'Denied']
        denial_analysis = denied_claims.groupby('denial_reason').size().reset_index(name='count')
        denial_analysis = denial_analysis.sort_values('count', ascending=False).head(10)
        denial_analysis['percentage'] = (denial_analysis['count'] / denial_analysis['count'].sum() * 100).round(1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_denial = px.bar(
                denial_analysis,
                x='count',
                y='denial_reason',
                orientation='h',
                color='count',
                color_continuous_scale='Reds',
                labels={'count': 'Number of Denials', 'denial_reason': 'Denial Reason'}
            )
            st.plotly_chart(fig_denial, use_container_width=True)
        
        with col2:
            st.dataframe(denial_analysis, hide_index=True, use_container_width=True)
    
    with tab2:
        st.markdown("### Provider Performance")
        
        claims_with_provider = claims.merge(providers[['provider_id', 'provider_type']], on='provider_id')
        
        provider_analysis = claims_with_provider.groupby('provider_type').agg({
            'claim_id': 'count',
            'paid_amount': 'sum',
        }).reset_index()
        provider_analysis.columns = ['provider_type', 'total_claims', 'total_paid']
        
        denied_count = claims_with_provider[claims_with_provider['claim_status'] == 'Denied'].groupby('provider_type').size()
        provider_analysis = provider_analysis.merge(
            denied_count.reset_index(name='denied_count'),
            left_on='provider_type',
            right_on='provider_type',
            how='left'
        )
        provider_analysis['denial_rate'] = (provider_analysis['denied_count'] / provider_analysis['total_claims'] * 100).round(1)
        
        fig_provider = px.bar(
            provider_analysis,
            x='provider_type',
            y=['total_claims'],
            barmode='group',
            labels={'value': 'Number of Claims', 'provider_type': 'Provider Type'},
            color_discrete_sequence=['#3498db']
        )
        st.plotly_chart(fig_provider, use_container_width=True)
        
        st.dataframe(provider_analysis, hide_index=True, use_container_width=True)
    
    with tab3:
        st.markdown("### Geographic Analysis")
        
        claims_with_state = claims.merge(providers[['provider_id', 'state']], on='provider_id')
        
        state_analysis = claims_with_state.groupby('state').agg({
            'claim_id': 'count',
            'allowed_amount': 'sum',
        }).reset_index()
        state_analysis.columns = ['state', 'claim_count', 'total_allowed']
        
        denied_by_state = claims_with_state[claims_with_state['claim_status'] == 'Denied'].groupby('state').size()
        state_analysis = state_analysis.merge(
            denied_by_state.reset_index(name='denied_count'),
            left_on='state',
            right_on='state',
            how='left'
        )
        state_analysis['denial_rate'] = (state_analysis['denied_count'] / state_analysis['claim_count'] * 100).round(1)
        state_analysis = state_analysis.sort_values('denial_rate', ascending=False)
        
        fig_state = px.bar(
            state_analysis,
            x='state',
            y='claim_count',
            color='denial_rate',
            color_continuous_scale='RdYlGn_r',
            labels={'state': 'State', 'claim_count': 'Claims', 'denial_rate': 'Denial Rate (%)'}
        )
        st.plotly_chart(fig_state, use_container_width=True)
        
        st.dataframe(state_analysis, hide_index=True, use_container_width=True)
    
    with tab4:
        st.markdown("### Claims Trend Over Time")
        
        claims['claim_month'] = pd.to_datetime(claims['claim_date']).dt.to_period('M')
        
        monthly_claims = claims.groupby('claim_month').agg({
            'claim_id': 'count',
            'paid_amount': 'sum',
        }).reset_index()
        monthly_claims.columns = ['month', 'claim_count', 'total_paid']
        monthly_claims['month'] = monthly_claims['month'].astype(str)
        
        fig_trend = px.line(
            monthly_claims,
            x='month',
            y='claim_count',
            markers=True,
            labels={'month': 'Month', 'claim_count': 'Number of Claims'}
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.dataframe(monthly_claims, hide_index=True, use_container_width=True)

# ============================================================================
# PAGE 3: DETAILED ANALYSIS
# ============================================================================

elif page == "🔍 Detailed Analysis":
    st.markdown("## 🔍 Detailed Analysis")
    st.divider()
    
    analysis_type = st.selectbox(
        "Select Analysis Type:",
        ["High-Risk Providers", "High-Risk Claims", "Claims by Procedure", "Member Analysis"]
    )
    
    if analysis_type == "High-Risk Providers":
        st.markdown("### High-Risk Providers (Denial Rate > 25%)")
        
        claims_with_provider = claims.merge(providers[['provider_id', 'provider_name', 'provider_type']], on='provider_id')
        
        provider_risk = claims_with_provider.groupby(['provider_id', 'provider_name', 'provider_type']).agg({
            'claim_id': 'count',
            'allowed_amount': 'sum',
        }).reset_index()
        provider_risk.columns = ['provider_id', 'provider_name', 'provider_type', 'total_claims', 'total_allowed']
        
        denied_count = claims_with_provider[claims_with_provider['claim_status'] == 'Denied'].groupby('provider_id').size()
        provider_risk = provider_risk.merge(
            denied_count.reset_index(name='denied_count'),
            left_on='provider_id',
            right_on='provider_id',
            how='left'
        )
        provider_risk['denial_rate'] = (provider_risk['denied_count'] / provider_risk['total_claims'] * 100).round(1)
        
        high_risk = provider_risk[provider_risk['denial_rate'] > 25].sort_values('denial_rate', ascending=False)
        
        if len(high_risk) > 0:
            st.warning(f"⚠️ {len(high_risk)} providers have denial rates > 25%")
            st.dataframe(high_risk[['provider_name', 'provider_type', 'total_claims', 'denial_rate']], 
                        hide_index=True, use_container_width=True)
        else:
            st.info("No high-risk providers found")
    
    elif analysis_type == "High-Risk Claims":
        st.markdown("### High-Risk Claims")
        
        high_risk_reasons = ['Pre-authorization Required', 'Out of Network', 'Incomplete Documentation']
        high_risk_claims = claims[claims['denial_reason'].isin(high_risk_reasons)]
        
        st.warning(f"⚠️ {len(high_risk_claims):,} claims identified as high-risk")
        st.info(f"💰 Amount at risk: ${high_risk_claims['allowed_amount'].sum():,.2f}")
        
        risk_summary = pd.DataFrame({
            'Risk Factor': high_risk_reasons,
            'Count': [len(claims[claims['denial_reason'] == reason]) for reason in high_risk_reasons],
        })
        
        st.dataframe(risk_summary, hide_index=True, use_container_width=True)
    
    elif analysis_type == "Claims by Procedure":
        st.markdown("### Denial Rate by Procedure Code")
        
        procedure_analysis = claims.groupby('procedure_code').agg({
            'claim_id': 'count',
            'allowed_amount': 'sum',
        }).reset_index()
        procedure_analysis.columns = ['procedure_code', 'total_claims', 'total_allowed']
        
        denied_by_proc = claims[claims['claim_status'] == 'Denied'].groupby('procedure_code').size()
        procedure_analysis = procedure_analysis.merge(
            denied_by_proc.reset_index(name='denied_count'),
            left_on='procedure_code',
            right_on='procedure_code',
            how='left'
        )
        procedure_analysis['denial_rate'] = (procedure_analysis['denied_count'] / procedure_analysis['total_claims'] * 100).round(1)
        procedure_analysis = procedure_analysis.sort_values('denial_rate', ascending=False)
        
        fig = px.bar(
            procedure_analysis,
            x='procedure_code',
            y='denial_rate',
            color='denial_rate',
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(procedure_analysis, hide_index=True, use_container_width=True)
    
    elif analysis_type == "Member Analysis":
        st.markdown("### Top Claims Users")
        
        claims_with_member = claims.merge(members[['member_id', 'plan_type']], on='member_id')
        
        member_analysis = claims_with_member.groupby('member_id').agg({
            'claim_id': 'count',
            'allowed_amount': 'sum',
            'paid_amount': 'sum',
        }).reset_index()
        member_analysis.columns = ['member_id', 'claim_count', 'total_allowed', 'total_paid']
        member_analysis = member_analysis.sort_values('claim_count', ascending=False).head(20)
        
        st.dataframe(member_analysis, hide_index=True, use_container_width=True)

# ============================================================================
# PAGE 4: FINANCIAL
# ============================================================================

elif page == "💰 Financial":
    st.markdown("## 💰 Financial Analysis")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    total_billed = claims['billed_amount'].sum()
    total_allowed = claims['allowed_amount'].sum()
    total_paid = claims['paid_amount'].sum()
    
    with col1:
        st.metric("Total Billed", f"${total_billed/1e6:.2f}M")
    with col2:
        st.metric("Total Allowed", f"${total_allowed/1e6:.2f}M")
    with col3:
        st.metric("Total Paid", f"${total_paid/1e6:.2f}M")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Financial Breakdown")
        
        financial_data = pd.DataFrame({
            'Category': ['Billed', 'Allowed', 'Paid', 'Denied/Pending'],
            'Amount': [
                total_billed,
                total_allowed,
                total_paid,
                total_allowed - total_paid
            ]
        })
        
        fig = px.pie(
            financial_data,
            values='Amount',
            names='Category',
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Payment Ratio Analysis")
        
        payment_ratio = (total_paid / total_allowed * 100)
        denial_impact = (total_allowed - total_paid)
        
        st.info(f"""
        **Payment Ratio:** {payment_ratio:.1f}%
        
        **Amount Not Paid:** ${denial_impact/1e6:.2f}M
        
        **Avg Claim Amount:** ${total_allowed/len(claims):.2f}
        
        **Avg Paid Amount:** ${total_paid/len(claims):.2f}
        """)
    
    st.divider()
    
    st.markdown("### Financial Summary by Claim Status")
    
    financial_summary = claims.groupby('claim_status').agg({
        'billed_amount': 'sum',
        'allowed_amount': 'sum',
        'paid_amount': 'sum',
    }).reset_index()
    financial_summary.columns = ['Status', 'Billed', 'Allowed', 'Paid']
    
    st.dataframe(financial_summary, hide_index=True, use_container_width=True)

# ============================================================================
# PAGE 5: SETTINGS
# ============================================================================

elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings & Information")
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Data Information")
        st.info(f"""
        **Total Claims:** {len(claims):,}
        
        **Total Members:** {len(members):,}
        
        **Total Providers:** {len(providers):,}
        
        **Data Range:** 2023
        
        **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
    
    with col2:
        st.markdown("### Application Info")
        st.info("""
        **App Name:** Healthcare Claims Analytics
        
        **Version:** 1.0
        
        **Technology:** Streamlit
        
        **Framework:** Python
        
        **Status:** Production Ready
        """)
    
    st.divider()
    
    st.markdown("### Data Export")
    
    if st.button("📥 Export All Data as CSV"):
        # Combine all analyses into exportable format
        export_data = claims.copy()
        
        st.success("✓ Data ready for export")
        st.download_button(
            label="Download Claims Data (CSV)",
            data=export_data.to_csv(index=False),
            file_name="claims_data.csv",
            mime="text/csv"
        )
    
    st.divider()
    
    st.markdown("### About This Dashboard")
    st.markdown("""
    This Healthcare Claims Analytics Platform provides comprehensive insights into 
    healthcare claims processing, denial patterns, and operational efficiency.
    
    **Features:**
    - Real-time claims analysis
    - Denial pattern identification
    - Provider performance metrics
    - Geographic analysis
    - Financial impact reporting
    
    **Built with:** Streamlit, Plotly, Pandas
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Healthcare Claims Analytics Platform | Elevance Health Experience</p>
    <p>© 2024 | Data Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)
