from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash,
    send_file,
    jsonify
)
import os

# Import original fixed ecommerce analytics
from spark_jobs.sales_analysis import (
    get_total_sales,
    get_total_profit,
    get_total_orders,
    get_avg_discount,
    get_region_sales,
    get_category_sales,
    get_monthly_sales,
    get_segment_sales,
    get_top_products,
    get_filtered_dashboard_data
)

# Import report generator functions
from spark_jobs.report_generator import (
    generate_sales_pdf,
    generate_sales_excel,
    generate_prediction_pdf,
    get_spark_dataset_summary
)

# Import new dynamic intelligent analyzer
from spark_jobs.dynamic_analysis import analyze_dataset

app = Flask(__name__)
app.secret_key = 'pulse_super_secret_key_123'

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# FIXED ECOMMERCE DATASET
ECOMMERCE_DATASET_PATH = 'sales.csv'

def format_number(num):
    is_negative = num < 0
    abs_num = abs(num)
    
    if abs_num >= 10000000:
        res = f"{round(abs_num / 10000000, 2)}Cr"
    elif abs_num >= 100000:
        res = f"{round(abs_num / 100000, 2)}L"
    elif abs_num >= 1000:
        res = f"{round(abs_num / 1000, 2)}K"
    else:
        res = str(round(abs_num, 2))
        
    return f"-{res}" if is_negative else res

def format_currency(num):
    formatted = format_number(num)
    return f"-₹{formatted[1:]}" if formatted.startswith('-') else f"₹{formatted}"

# ==========================================
# SYSTEM 1: FIXED ECOMMERCE DASHBOARD
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    dataset_path = ECOMMERCE_DATASET_PATH
    data = get_filtered_dashboard_data(dataset_path)
    
    formatted_top_products = []
    for p in data['top_products']:
        profit = p['total_profit_raw']
        formatted_top_products.append({
            'Product Name': p['Product Name'],
            'total_sales': format_currency(p['total_sales_raw']),
            'total_profit': format_currency(profit),
            'profit_class': 'text-green' if profit >= 0 else 'text-danger'
        })
    
    return render_template(
        'dashboard.html',
        years=data['years'],
        total_sales=format_currency(data['total_sales']),
        total_profit=format_currency(data['total_profit']),
        total_orders=f"{data['total_orders']:,}",
        avg_discount=data['avg_discount'],
        regions=data['regions'],
        region_values=data['region_values'],
        categories=data['categories'],
        category_values=data['category_values'],
        months=data['months'],
        month_values=data['month_values'],
        segments=data['segments'],
        segment_values=data['segment_values'],
        top_products=formatted_top_products,
        forecast_value=format_currency(data['forecast']['forecast_value']),
        forecast_trend=f"{'+' if data['forecast']['forecast_trend'] >= 0 else ''}{data['forecast']['forecast_trend']}%",
        trend_class=data['forecast']['trend_class'],
        forecast_accuracy=f"{data['forecast']['forecast_accuracy']}%"
    )

@app.route('/api/dashboard-data')
def api_dashboard_data():
    dataset_path = ECOMMERCE_DATASET_PATH
    year_val = request.args.get('year', 'All')
    region_val = request.args.get('region', 'All')
    category_val = request.args.get('category', 'All')
    search_val = request.args.get('search', '')
    
    data = get_filtered_dashboard_data(
        dataset_path,
        year_filter=year_val,
        region_filter=region_val,
        category_filter=category_val,
        search_query=search_val
    )
    
    formatted_top_products = []
    for p in data['top_products']:
        profit = p['total_profit_raw']
        formatted_top_products.append({
            'Product Name': p['Product Name'],
            'total_sales': format_currency(p['total_sales_raw']),
            'total_profit': format_currency(profit),
            'profit_class': 'text-green' if profit >= 0 else 'text-danger'
        })
        
    return {
        'total_sales': format_currency(data['total_sales']),
        'total_profit': format_currency(data['total_profit']),
        'total_orders': f"{data['total_orders']:,}",
        'avg_discount': f"{data['avg_discount']}%",
        'regions': data['regions'],
        'region_values': data['region_values'],
        'categories': data['categories'],
        'category_values': data['category_values'],
        'months': data['months'],
        'month_values': data['month_values'],
        'segments': data['segments'],
        'segment_values': data['segment_values'],
        'top_products': formatted_top_products,
        'forecast_value': format_currency(data['forecast']['forecast_value']),
        'forecast_trend': f"{'+' if data['forecast']['forecast_trend'] >= 0 else ''}{data['forecast']['forecast_trend']}%",
        'trend_class': data['forecast']['trend_class'],
        'forecast_accuracy': f"{data['forecast']['forecast_accuracy']}%",
        'forecast_labels': data['forecast']['forecast_labels'],
        'forecast_values': data['forecast']['forecast_values'],
        'historical_forecast_labels': data['forecast']['historical_labels'],
        'historical_forecast_values': data['forecast']['historical_values']
    }

@app.route('/analytics')
def analytics():
    dataset_path = ECOMMERCE_DATASET_PATH
    data = get_filtered_dashboard_data(dataset_path)
    forecast = data['forecast']
    
    return render_template(
        'analytics.html',
        prediction_accuracy=f"{forecast['forecast_accuracy']}%",
        historical_labels=forecast['historical_labels'],
        historical_values=forecast['historical_values'],
        forecast_labels=forecast['forecast_labels'],
        forecast_values=forecast['forecast_values']
    )

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/reports/export/pdf')
def export_pdf():
    dataset_path = ECOMMERCE_DATASET_PATH
    year = request.args.get('year', 'All')
    region = request.args.get('region', 'All')
    category = request.args.get('category', 'All')
    
    pdf_buffer = generate_sales_pdf(dataset_path, year, region, category)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"sales_report_{year}_{region}_{category}.pdf",
        mimetype="application/pdf"
    )

@app.route('/reports/export/excel')
def export_excel():
    dataset_path = ECOMMERCE_DATASET_PATH
    year = request.args.get('year', 'All')
    region = request.args.get('region', 'All')
    category = request.args.get('category', 'All')
    
    excel_buffer = generate_sales_excel(dataset_path, year, region, category)
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=f"sales_report_{year}_{region}_{category}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/reports/generate/forecast')
def generate_forecast_report():
    dataset_path = ECOMMERCE_DATASET_PATH
    pdf_buffer = generate_prediction_pdf(dataset_path)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="ml_sales_forecast_report.pdf",
        mimetype="application/pdf"
    )

# Added alias route with trailing slash for compatibility
@app.route('/reports/generate/forecast/')
def generate_forecast_report_slash():
    return generate_forecast_report()

@app.route('/api/reports/dataset-summary')
def api_dataset_summary():
    dataset_path = ECOMMERCE_DATASET_PATH
    summary = get_spark_dataset_summary(dataset_path)
    return jsonify(summary)

# ==========================================
# SYSTEM 2: DYNAMIC DATASET ANALYZER
# ==========================================

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            session['dynamic_dataset_path'] = path
            try:
                from spark_jobs.dynamic_analysis import preload_dynamic_dataset
                preload_dynamic_dataset(path)
            except Exception:
                pass
            return redirect('/dynamic-dashboard')
        else:
            flash("Please upload a valid CSV file.")
    return render_template('upload.html')


@app.route('/dynamic-dashboard')
def dynamic_dashboard():
    dataset_path = session.get('dynamic_dataset_path')

    if not dataset_path or not os.path.exists(dataset_path):
        flash("No valid dataset found. Please upload a dataset first.")
        return redirect('/upload')

    analysis = analyze_dataset(dataset_path)

    if not analysis or not analysis.get('success'):
        flash(f"Error processing dataset: {analysis.get('error', 'Unknown Error')}")
        return redirect('/upload')

    return render_template(
        'dynamic_dashboard.html',
        filename=analysis.get('filename', 'dataset.csv'),
        shape=analysis['shape'],
        columns=analysis['columns'],
        preview_data=analysis['preview_data'],
        preview_sort_col=analysis.get('preview_sort_col'),
        kpis=analysis['kpis'],
        charts=analysis['charts'],
        insights=analysis.get('insights', []),
        top_items=analysis.get('top_items', []),
        top_items_label_col=analysis.get('top_items_label_col', 'Item'),
        top_items_value_col=analysis.get('top_items_value_col', 'Value'),
        forecast=analysis.get('forecast'),
        filter_cols=analysis.get('filter_cols', {})
    )


@app.route('/api/dynamic-dashboard-data')
def api_dynamic_dashboard_data():
    dataset_path = session.get('dynamic_dataset_path')

    if not dataset_path or not os.path.exists(dataset_path):
        return jsonify({'success': False, 'error': 'No dataset in session'}), 400

    # Collect all filter params sent from the frontend
    filters = {}
    for key, val in request.args.items():
        if key.startswith('filter_') and val and val != 'All':
            col_name = key[len('filter_'):]
            filters[col_name] = val

    analysis = analyze_dataset(dataset_path, filters=filters)

    if not analysis or not analysis.get('success'):
        return jsonify({'success': False, 'error': analysis.get('error', 'Unknown')}), 500

    return jsonify({
        'success': True,
        'shape': analysis['shape'],
        'kpis': analysis['kpis'],
        'charts': analysis['charts'],
        'top_items': analysis.get('top_items', []),
        'top_items_label_col': analysis.get('top_items_label_col', 'Item'),
        'top_items_value_col': analysis.get('top_items_value_col', 'Value'),
        'forecast': analysis.get('forecast'),
        'insights': analysis.get('insights', [])
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def _warmup_backend():
    """Start Spark JVM + preload sales.csv before the first browser request."""
    print("Pulse: warming up Spark and preloading dataset...")
    try:
        from spark_jobs.spark_session import warm_spark
        from spark_jobs.sales_analysis import preload_dataset

        warm_spark()
        if os.path.exists(ECOMMERCE_DATASET_PATH):
            preload_dataset(ECOMMERCE_DATASET_PATH)
            # Pre-run dashboard aggregations so the first browser click is instant
            get_filtered_dashboard_data(ECOMMERCE_DATASET_PATH)
            print("Pulse: ready — open http://127.0.0.1:5000/dashboard")
        else:
            print("Pulse: Spark ready (sales.csv not found; upload flow still works)")
    except Exception as exc:
        print(f"Pulse: warmup warning — {exc}")


if __name__ == '__main__':
    # use_reloader=False prevents Flask from spawning a child process that
    # orphans the Spark JVM on Windows (ConnectionRefusedError / WinError 10061)
    _warmup_backend()
    app.run(debug=True, use_reloader=False)