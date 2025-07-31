# oscilloscope_analyzer.py
import sys
import os
import csv
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import psycopg2
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QTabWidget,
                             QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
                             QGroupBox, QFormLayout, QCheckBox, QProgressBar, QSplitter,
                             QScrollArea, QFrame, QDateEdit, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            'host': 'localhost',
            'database': 'oscilloscope_db',
            'user': 'oscuser',
            'password': 'oscpassword123',
            'port': '5432'
        }
        
    def connect(self):
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def save_analysis(self, test_type, data):
        conn = self.connect()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            table_name = f"{test_type.lower().replace(' ', '_')}_analysis"
            
            columns = list(data.keys())
            values = list(data.values())
            placeholders = ', '.join(['%s'] * len(values))
            
            query = f"""
            INSERT INTO {table_name} ({', '.join(columns)}) 
            VALUES ({placeholders})
            """
            
            cursor.execute(query, values)
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Database save error: {e}")
            return False
        finally:
            conn.close()
    
    def get_results(self, test_type, limit=100):
        conn = self.connect()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            table_name = f"{test_type.lower().replace(' ', '_')}_analysis"
            
            cursor.execute(f"""
                SELECT * FROM {table_name} 
                ORDER BY analysis_date DESC 
                LIMIT %s
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            print(f"Database query error: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_results(self, filters=None):
        """Get results from all tables with optional filters"""
        conn = self.connect()
        if not conn:
            return []
            
        all_results = []
        tables = ['dtt_analysis', 'dtr_analysis', 'dc02_analysis', 'dc03_skid_analysis', 'idod_analysis']
        
        try:
            cursor = conn.cursor()
            
            for table in tables:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table,))
                
                if not cursor.fetchone()[0]:
                    continue
                
                # Build query with filters
                query = f"SELECT *, '{table}' as source_table FROM {table}"
                where_conditions = []
                params = []
                
                if filters:
                    if filters.get('test_type') and filters['test_type'] != 'All':
                        table_test_type = table.replace('_analysis', '').upper().replace('_', ' ')
                        if table_test_type != filters['test_type'].upper():
                            continue
                    
                    if filters.get('pass_fail') and filters['pass_fail'] != 'All':
                        where_conditions.append("pass_fail = %s")
                        params.append(filters['pass_fail'].lower())
                    
                    if filters.get('tester_id'):
                        where_conditions.append("tester_id ILIKE %s")
                        params.append(f"%{filters['tester_id']}%")
                    
                    if filters.get('test_bench'):
                        where_conditions.append("test_bench ILIKE %s")
                        params.append(f"%{filters['test_bench']}%")
                    
                    if filters.get('date_from'):
                        where_conditions.append("test_date >= %s")
                        params.append(filters['date_from'])
                    
                    if filters.get('date_to'):
                        where_conditions.append("test_date <= %s")
                        params.append(filters['date_to'])
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                query += " ORDER BY analysis_date DESC"
                
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                
                for row in results:
                    result_dict = dict(zip(columns, row))
                    result_dict['test_type'] = table.replace('_analysis', '').upper().replace('_', ' ')
                    all_results.append(result_dict)
            
            return all_results
            
        except Exception as e:
            print(f"Database query error: {e}")
            return []
        finally:
            conn.close()
    
    def get_analytics_summary(self, filters=None):
        """Get summary statistics for analytics"""
        results = self.get_all_results(filters)
        
        if not results:
            return {}
        
        # Basic counts
        total_tests = len(results)
        pass_count = len([r for r in results if r.get('pass_fail') == 'pass'])
        fail_count = total_tests - pass_count
        pass_rate = (pass_count / total_tests * 100) if total_tests > 0 else 0
        
        # Test type breakdown
        test_types = {}
        for result in results:
            test_type = result.get('test_type', 'Unknown')
            if test_type not in test_types:
                test_types[test_type] = {'total': 0, 'pass': 0, 'fail': 0}
            test_types[test_type]['total'] += 1
            if result.get('pass_fail') == 'pass':
                test_types[test_type]['pass'] += 1
            else:
                test_types[test_type]['fail'] += 1
        
        # Tester performance
        testers = {}
        for result in results:
            tester = result.get('tester_id', 'Unknown')
            if tester not in testers:
                testers[tester] = {'total': 0, 'pass': 0, 'fail': 0}
            testers[tester]['total'] += 1
            if result.get('pass_fail') == 'pass':
                testers[tester]['pass'] += 1
            else:
                testers[tester]['fail'] += 1
        
        # Test bench performance
        test_benches = {}
        for result in results:
            bench = result.get('test_bench', 'Unknown')
            if bench not in test_benches:
                test_benches[bench] = {'total': 0, 'pass': 0, 'fail': 0}
            test_benches[bench]['total'] += 1
            if result.get('pass_fail') == 'pass':
                test_benches[bench]['pass'] += 1
            else:
                test_benches[bench]['fail'] += 1
        
        # Recent trends (last 30 days)
        recent_date = datetime.now().date() - timedelta(days=30)
        recent_results = [r for r in results if r.get('test_date') and r['test_date'] >= recent_date]
        recent_pass_rate = (len([r for r in recent_results if r.get('pass_fail') == 'pass']) / len(recent_results) * 100) if recent_results else 0
        
        # Parameter statistics
        peak_to_peak_values = [float(r.get('peak_to_peak_mv', 0)) for r in results if r.get('peak_to_peak_mv')]
        trigger_current_values = [float(r.get('trigger_current_a', 0)) for r in results if r.get('trigger_current_a')]
        noise_values = [float(r.get('noise_mv', 0)) for r in results if r.get('noise_mv')]
        
        return {
            'summary': {
                'total_tests': total_tests,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': pass_rate,
                'recent_pass_rate': recent_pass_rate,
                'recent_tests': len(recent_results)
            },
            'test_types': test_types,
            'testers': testers,
            'test_benches': test_benches,
            'parameters': {
                'peak_to_peak': {
                    'mean': np.mean(peak_to_peak_values) if peak_to_peak_values else 0,
                    'std': np.std(peak_to_peak_values) if peak_to_peak_values else 0,
                    'min': min(peak_to_peak_values) if peak_to_peak_values else 0,
                    'max': max(peak_to_peak_values) if peak_to_peak_values else 0
                },
                'trigger_current': {
                    'mean': np.mean(trigger_current_values) if trigger_current_values else 0,
                    'std': np.std(trigger_current_values) if trigger_current_values else 0,
                    'min': min(trigger_current_values) if trigger_current_values else 0,
                    'max': max(trigger_current_values) if trigger_current_values else 0
                },
                'noise': {
                    'mean': np.mean(noise_values) if noise_values else 0,
                    'std': np.std(noise_values) if noise_values else 0,
                    'min': min(noise_values) if noise_values else 0,
                    'max': max(noise_values) if noise_values else 0
                }
            }
        }

class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    
    def __init__(self, file_path, trigger_current):
        super().__init__()
        self.file_path = file_path
        self.trigger_current = trigger_current
        
    def run(self):
        try:
            self.progress.emit(10)
            data = self.load_csv_data(self.file_path)
            
            self.progress.emit(30)
            analysis = self.calculate_analysis(data, self.trigger_current)
            
            self.progress.emit(100)
            self.finished.emit(analysis)
            
        except Exception as e:
            print(f"Analysis error: {e}")
            self.finished.emit({})
    
    def load_csv_data(self, file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        data_start = -1
        for i, line in enumerate(lines):
            if 'TIME,CH1,CH2' in line:
                data_start = i
                break
        
        if data_start == -1:
            raise ValueError("Could not find data header in CSV file")
        
        data = []
        for line in lines[data_start + 1:]:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        time = float(parts[0]) * 1000
                        ch1 = float(parts[1])
                        ch2 = float(parts[2])
                        data.append({'time': time, 'ch1': ch1, 'ch2': ch2})
                    except ValueError:
                        continue
        
        return data
    
    def calculate_analysis(self, data, trigger_threshold):
        if not data:
            return {}
        
        times = [d['time'] for d in data]
        ch1_values = [d['ch1'] for d in data]
        ch2_values = [d['ch2'] for d in data]
        
        ch1_min, ch1_max = min(ch1_values), max(ch1_values)
        ch1_peak_to_peak = (ch1_max - ch1_min) * 1000
        
        ch2_min, ch2_max = min(ch2_values), max(ch2_values)
        ch2_peak_to_peak = ch2_max - ch2_min
        
        ch1_rms = np.sqrt(np.mean([v**2 for v in ch1_values]))
        ch2_rms = np.sqrt(np.mean([v**2 for v in ch2_values]))
        
        ch1_mean = np.mean(ch1_values)
        ch1_noise = np.std(ch1_values) * 1000
        
        trigger_points = []
        in_trigger = False
        
        for i in range(1, len(data)):
            prev_current = abs(data[i-1]['ch2'])
            current_current = abs(data[i]['ch2'])
            
            if not in_trigger and current_current > trigger_threshold and prev_current <= trigger_threshold:
                trigger_points.append({
                    'time': data[i]['time'],
                    'index': i,
                    'current': data[i]['ch2']
                })
                in_trigger = True
            elif in_trigger and current_current <= trigger_threshold:
                in_trigger = False
        
        ringdown = self.calculate_ringdown(ch1_values)
        
        if len(times) > 1:
            duration = max(times) - min(times)
            sample_rate = len(times) / (duration / 1000) if duration > 0 else 0
        else:
            sample_rate = 0
        
        return {
            'raw_data': data,
            'ch1': {
                'min': ch1_min,
                'max': ch1_max,
                'peak_to_peak': ch1_peak_to_peak,
                'rms': ch1_rms,
                'noise': ch1_noise,
                'ringdown': ringdown
            },
            'ch2': {
                'min': ch2_min,
                'max': ch2_max,
                'peak_to_peak': ch2_peak_to_peak,
                'rms': ch2_rms
            },
            'trigger': {
                'threshold': trigger_threshold,
                'points': trigger_points,
                'count': len(trigger_points)
            },
            'metadata': {
                'data_points': len(data),
                'sample_rate': sample_rate,
                'duration': max(times) - min(times) if times else 0,
                'time_start': min(times) if times else 0,
                'time_end': max(times) if times else 0
            }
        }
    
    def calculate_ringdown(self, values):
        if len(values) < 50:
            return {'ringdown_voltage': 0, 'decay_constant': 0}
        
        abs_values = [abs(v) for v in values]
        max_idx = abs_values.index(max(abs_values))
        
        if max_idx >= len(values) - 20:
            return {'ringdown_voltage': 0, 'decay_constant': 0}
        
        decay_segment = values[max_idx:min(max_idx + 100, len(values))]
        initial_amp = abs(decay_segment[0])
        final_amp = abs(decay_segment[-1])
        
        ringdown_voltage = (initial_amp - final_amp) * 1000
        
        return {
            'ringdown_voltage': ringdown_voltage,
            'decay_constant': np.log(initial_amp / final_amp) / len(decay_segment) if initial_amp > final_amp > 0 else 0
        }

class MatplotlibWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
    def plot_data(self, analysis_data, trigger_current, zoom_range=(0, 100)):
        self.figure.clear()
        
        if not analysis_data or 'raw_data' not in analysis_data:
            self.canvas.draw()
            return
        
        data = analysis_data['raw_data']
        if not data:
            self.canvas.draw()
            return
        
        times = [d['time'] for d in data]
        ch1_values = [d['ch1'] for d in data]
        ch2_values = [d['ch2'] for d in data]
        
        start_idx = int(len(data) * zoom_range[0] / 100)
        end_idx = int(len(data) * zoom_range[1] / 100)
        
        plot_times = times[start_idx:end_idx]
        plot_ch1 = ch1_values[start_idx:end_idx]
        plot_ch2 = ch2_values[start_idx:end_idx]
        
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212)
        
        ax1.plot(plot_times, plot_ch1, 'g-', linewidth=1, label='CH1 (Voltage)')
        ax1.set_ylabel('Voltage (V)')
        ax1.set_title('Channel 1 - Voltage')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.plot(plot_times, plot_ch2, 'b-', linewidth=1, label='CH2 (Current)')
        ax2.axhline(y=trigger_current, color='r', linestyle='--', alpha=0.7, label=f'Trigger +{trigger_current}A')
        ax2.axhline(y=-trigger_current, color='r', linestyle='--', alpha=0.7, label=f'Trigger -{trigger_current}A')
        ax2.set_xlabel('Time (ms)')
        ax2.set_ylabel('Current (A)')
        ax2.set_title('Channel 2 - Current')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        trigger_points = analysis_data.get('trigger', {}).get('points', [])
        for point in trigger_points:
            if start_idx <= point['index'] < end_idx:
                ax2.axvline(x=point['time'], color='orange', linestyle=':', alpha=0.8)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_analytics_charts(self, summary_data):
        self.figure.clear()
        
        if not summary_data:
            self.canvas.draw()
            return
        
        ax1 = self.figure.add_subplot(221)
        ax2 = self.figure.add_subplot(222)
        ax3 = self.figure.add_subplot(223)
        ax4 = self.figure.add_subplot(224)
        
        summary = summary_data.get('summary', {})
        if summary.get('total_tests', 0) > 0:
            labels = ['Pass', 'Fail']
            sizes = [summary.get('pass_count', 0), summary.get('fail_count', 0)]
            colors = ['#4CAF50', '#F44336']
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title(f'Overall Results\n({summary.get("total_tests", 0)} tests)')
        
        test_types = summary_data.get('test_types', {})
        if test_types:
            types = list(test_types.keys())
            pass_rates = [test_types[t]['pass'] / test_types[t]['total'] * 100 if test_types[t]['total'] > 0 else 0 for t in types]
            
            bars = ax2.bar(types, pass_rates, color='#2196F3', alpha=0.7)
            ax2.set_title('Pass Rate by Test Type')
            ax2.set_ylabel('Pass Rate (%)')
            ax2.set_ylim(0, 100)
            
            for bar, rate in zip(bars, pass_rates):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{rate:.1f}%', ha='center', va='bottom')
        
        parameters = summary_data.get('parameters', {})
        peak_to_peak = parameters.get('peak_to_peak', {})
        if peak_to_peak.get('mean', 0) > 0 and peak_to_peak.get('std', 0) > 0:
            mean = peak_to_peak['mean']
            std = peak_to_peak['std']
            x = np.linspace(max(0, mean - 3*std), mean + 3*std, 100)
            y = (1/(std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
            ax3.plot(x, y, 'g-', linewidth=2)
            ax3.axvline(mean, color='r', linestyle='--', alpha=0.7, label=f'Mean: {mean:.1f}mV')
            ax3.set_title('Peak-to-Peak Distribution')
            ax3.set_xlabel('Peak-to-Peak (mV)')
            ax3.set_ylabel('Probability Density')
            ax3.legend()
        
        testers = summary_data.get('testers', {})
        if testers:
            tester_names = list(testers.keys())
            tester_pass_rates = [testers[t]['pass'] / testers[t]['total'] * 100 if testers[t]['total'] > 0 else 0 for t in tester_names]
            
            bars = ax4.barh(tester_names, tester_pass_rates, color='#FF9800', alpha=0.7)
            ax4.set_title('Pass Rate by Tester')
            ax4.set_xlabel('Pass Rate (%)')
            ax4.set_xlim(0, 100)
            
            for bar, rate in zip(bars, tester_pass_rates):
                ax4.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                        f'{rate:.1f}%', ha='left', va='center')
        
        self.figure.tight_layout()
        self.canvas.draw()

class OscilloscopeAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oscilloscope Test System - PyQt6")
        self.setGeometry(100, 100, 1400, 1000)
        
        self.db_manager = DatabaseManager()
        self.current_analysis = None
        self.loaded_files = []
        
        self.test_type_configs = {
            'DTT': {
                'name': 'DTT',
                'dut_label': 'DTT (SV/33053/0020) [DUT]',
                'reference_label': 'DTR (SV/33053/0031) [Reference]',
                'has_ringdown': False
            },
            'DTR': {
                'name': 'DTR',
                'dut_label': 'DTR (SV/33053/0031) [DUT]',
                'reference_label': 'DTT (SV/33053/0020) [Reference]',
                'has_ringdown': False
            },
            'DC02': {
                'name': 'DC02',
                'dut_label': 'DC02 Innerblock (SV/103003/0016) [DUT]',
                'reference_label': 'DCbox (SV/102603/0033) [Reference]',
                'has_ringdown': True
            },
            'DC03 Skid': {
                'name': 'DC03 Skid',
                'dut_label': 'DC03 Skid (SV/102503/0026) [DUT]',
                'reference_label': 'DC03 Innerblock (SV/33053/0029) [Reference]',
                'has_ringdown': False
            },
            'IDOD': {
                'name': 'IDOD',
                'dut_label': 'IDOD skid [DUT]',
                'reference_label': 'IDOD Innerblock (SV/33053/0028) [Reference]',
                'has_ringdown': False,
                'has_skid_plate': True
            }
        }
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.setup_analysis_tab()
        self.setup_database_tab()
        self.setup_analytics_tab()
        self.setup_settings_tab()
        
    def setup_analysis_tab(self):
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        
        # File operations section
        file_group = QGroupBox("File Operations")
        file_layout = QHBoxLayout(file_group)
        
        self.load_file_btn = QPushButton("Load CSV File")
        self.load_file_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; }")
        
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("QLabel { color: #666; }")
        
        file_layout.addWidget(self.load_file_btn)
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        
        layout.addWidget(file_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Configuration and results
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Test configuration
        config_group = QGroupBox("Test Configuration")
        config_layout = QFormLayout(config_group)
        
        self.test_type_combo = QComboBox()
        self.test_type_combo.addItems(list(self.test_type_configs.keys()))
        config_layout.addRow("Test Type:", self.test_type_combo)
        
        self.test_number_edit = QLineEdit()
        config_layout.addRow("Test Number*:", self.test_number_edit)
        
        self.test_bench_edit = QLineEdit()
        config_layout.addRow("Test Bench*:", self.test_bench_edit)
        
        self.tester_id_edit = QLineEdit()
        config_layout.addRow("Tester ID*:", self.tester_id_edit)
        
        self.test_function_combo = QComboBox()
        self.test_function_combo.addItems([
            'Leak test', 'Performance test', 'Calibration test',
            'Endurance test', 'Temperature test', 'Vibration test', 'Pressure test'
        ])
        config_layout.addRow("Test Function:", self.test_function_combo)
        
        self.skid_plate_combo = QComboBox()
        self.skid_plate_combo.addItems(['100mm', '150mm', '200mm', '250mm', '300mm'])
        self.skid_plate_combo.setVisible(False)
        self.skid_plate_label = QLabel("Skid Plate Diameter:")
        self.skid_plate_label.setVisible(False)
        config_layout.addRow(self.skid_plate_label, self.skid_plate_combo)
        
        left_layout.addWidget(config_group)
        
        # Analysis settings
        settings_group = QGroupBox("Analysis Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.trigger_current_spin = QDoubleSpinBox()
        self.trigger_current_spin.setRange(0.1, 100.0)
        self.trigger_current_spin.setValue(1.0)
        self.trigger_current_spin.setSuffix(" A")
        settings_layout.addRow("Trigger Current:", self.trigger_current_spin)
        
        self.zoom_start_spin = QSpinBox()
        self.zoom_start_spin.setRange(0, 99)
        self.zoom_start_spin.setValue(0)
        self.zoom_start_spin.setSuffix(" %")
        settings_layout.addRow("Zoom Start:", self.zoom_start_spin)
        
        self.zoom_end_spin = QSpinBox()
        self.zoom_end_spin.setRange(1, 100)
        self.zoom_end_spin.setValue(100)
        self.zoom_end_spin.setSuffix(" %")
        settings_layout.addRow("Zoom End:", self.zoom_end_spin)
        
        left_layout.addWidget(settings_group)
        
        # Pass/Fail Criteria
        criteria_group = QGroupBox("Pass/Fail Criteria")
        criteria_layout = QFormLayout(criteria_group)
        
        # Peak to Peak
        peak_layout = QHBoxLayout()
        self.peak_lsl_spin = QDoubleSpinBox()
        self.peak_lsl_spin.setRange(0, 10000)
        self.peak_lsl_spin.setValue(150)
        self.peak_lsl_spin.setSuffix(" mV")
        self.peak_usl_spin = QDoubleSpinBox()
        self.peak_usl_spin.setRange(0, 10000)
        self.peak_usl_spin.setValue(400)
        self.peak_usl_spin.setSuffix(" mV")
        peak_layout.addWidget(QLabel("LSL:"))
        peak_layout.addWidget(self.peak_lsl_spin)
        peak_layout.addWidget(QLabel("USL:"))
        peak_layout.addWidget(self.peak_usl_spin)
        criteria_layout.addRow("Peak-to-Peak:", peak_layout)
        
        # Trigger Current
        trigger_layout = QHBoxLayout()
        self.trigger_lsl_spin = QDoubleSpinBox()
        self.trigger_lsl_spin.setRange(0, 1000)
        self.trigger_lsl_spin.setValue(30)
        self.trigger_lsl_spin.setSuffix(" A")
        self.trigger_usl_spin = QDoubleSpinBox()
        self.trigger_usl_spin.setRange(0, 1000)
        self.trigger_usl_spin.setValue(80)
        self.trigger_usl_spin.setSuffix(" A")
        trigger_layout.addWidget(QLabel("LSL:"))
        trigger_layout.addWidget(self.trigger_lsl_spin)
        trigger_layout.addWidget(QLabel("USL:"))
        trigger_layout.addWidget(self.trigger_usl_spin)
        criteria_layout.addRow("Trigger Current:", trigger_layout)
        
        # Noise
        noise_layout = QHBoxLayout()
        self.noise_lsl_spin = QDoubleSpinBox()
        self.noise_lsl_spin.setRange(0, 1000)
        self.noise_lsl_spin.setValue(0)
        self.noise_lsl_spin.setSuffix(" mV")
        self.noise_usl_spin = QDoubleSpinBox()
        self.noise_usl_spin.setRange(0, 1000)
        self.noise_usl_spin.setValue(5)
        self.noise_usl_spin.setSuffix(" mV")
        noise_layout.addWidget(QLabel("LSL:"))
        noise_layout.addWidget(self.noise_lsl_spin)
        noise_layout.addWidget(QLabel("USL:"))
        noise_layout.addWidget(self.noise_usl_spin)
        criteria_layout.addRow("Noise:", noise_layout)
        
        # Ringdown (for DC02)
        ringdown_layout = QHBoxLayout()
        self.ringdown_lsl_spin = QDoubleSpinBox()
        self.ringdown_lsl_spin.setRange(0, 1000)
        self.ringdown_lsl_spin.setValue(0)
        self.ringdown_lsl_spin.setSuffix(" mV")
        self.ringdown_usl_spin = QDoubleSpinBox()
        self.ringdown_usl_spin.setRange(0, 1000)
        self.ringdown_usl_spin.setValue(100)
        self.ringdown_usl_spin.setSuffix(" mV")
        ringdown_layout.addWidget(QLabel("LSL:"))
        ringdown_layout.addWidget(self.ringdown_lsl_spin)
        ringdown_layout.addWidget(QLabel("USL:"))
        ringdown_layout.addWidget(self.ringdown_usl_spin)
        self.ringdown_row = criteria_layout.addRow("Ringdown:", ringdown_layout)
        
        left_layout.addWidget(criteria_group)
        
        # Analysis results
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        # Pass/Fail indicator
        self.pass_fail_label = QLabel("Status: Not Analyzed")
        self.pass_fail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pass_fail_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; padding: 8px; }")
        results_layout.addWidget(self.pass_fail_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; }")
        self.analyze_btn.setEnabled(False)  # Disabled until file is loaded
        
        self.save_btn = QPushButton("Save to Database")
        self.save_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; padding: 8px; }")
        self.save_btn.setEnabled(False)
        
        button_layout.addWidget(self.analyze_btn)
        button_layout.addWidget(self.save_btn)
        results_layout.addLayout(button_layout)
        
        left_layout.addWidget(results_group)
        left_layout.addStretch()
        
        # Right panel - Chart
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Waveform Analysis"))
        
        self.chart_widget = MatplotlibWidget()
        right_layout.addWidget(self.chart_widget)
        
        # Set splitter proportions
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        
        self.tabs.addTab(analysis_widget, "Analysis")
        
    def setup_database_tab(self):
        db_widget = QWidget()
        layout = QVBoxLayout(db_widget)
        
        # Database connection info
        conn_group = QGroupBox("Database Connection")
        conn_layout = QFormLayout(conn_group)
        
        self.db_host_edit = QLineEdit("localhost")
        conn_layout.addRow("Host:", self.db_host_edit)
        
        self.db_port_edit = QLineEdit("5432")
        conn_layout.addRow("Port:", self.db_port_edit)
        
        self.db_name_edit = QLineEdit("oscilloscope_db")
        conn_layout.addRow("Database:", self.db_name_edit)
        
        self.db_user_edit = QLineEdit("oscuser")
        conn_layout.addRow("Username:", self.db_user_edit)
        
        self.db_password_edit = QLineEdit("oscpassword123")
        self.db_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addRow("Password:", self.db_password_edit)
        
        self.test_connection_btn = QPushButton("Test Connection")
        conn_layout.addRow("", self.test_connection_btn)
        
        layout.addWidget(conn_group)
        
        # Results table
        results_group = QGroupBox("Saved Results")
        results_layout = QVBoxLayout(results_group)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Test Type:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['All'] + list(self.test_type_configs.keys()))
        filter_layout.addWidget(self.filter_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        filter_layout.addWidget(self.refresh_btn)
        filter_layout.addStretch()
        
        results_layout.addLayout(filter_layout)
        
        # Results table
        self.results_table = QTableWidget()
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        self.tabs.addTab(db_widget, "Database")
    
    def setup_analytics_tab(self):
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)
        
        # Filters section
        filters_group = QGroupBox("Data Filters")
        filters_layout = QGridLayout(filters_group)
        
        # Test type filter
        filters_layout.addWidget(QLabel("Test Type:"), 0, 0)
        self.analytics_test_type_combo = QComboBox()
        self.analytics_test_type_combo.addItems(['All'] + list(self.test_type_configs.keys()))
        filters_layout.addWidget(self.analytics_test_type_combo, 0, 1)
        
        # Pass/Fail filter
        filters_layout.addWidget(QLabel("Result:"), 0, 2)
        self.analytics_pass_fail_combo = QComboBox()
        self.analytics_pass_fail_combo.addItems(['All', 'Pass', 'Fail'])
        filters_layout.addWidget(self.analytics_pass_fail_combo, 0, 3)
        
        # Tester filter
        filters_layout.addWidget(QLabel("Tester ID:"), 1, 0)
        self.analytics_tester_edit = QLineEdit()
        self.analytics_tester_edit.setPlaceholderText("Filter by tester...")
        filters_layout.addWidget(self.analytics_tester_edit, 1, 1)
        
        # Test bench filter
        filters_layout.addWidget(QLabel("Test Bench:"), 1, 2)
        self.analytics_bench_edit = QLineEdit()
        self.analytics_bench_edit.setPlaceholderText("Filter by test bench...")
        filters_layout.addWidget(self.analytics_bench_edit, 1, 3)
        
        # Date filters
        filters_layout.addWidget(QLabel("Date From:"), 2, 0)
        self.analytics_date_from = QDateEdit()
        self.analytics_date_from.setDate(QDate.currentDate().addDays(-30))
        self.analytics_date_from.setCalendarPopup(True)
        filters_layout.addWidget(self.analytics_date_from, 2, 1)
        
        filters_layout.addWidget(QLabel("Date To:"), 2, 2)
        self.analytics_date_to = QDateEdit()
        self.analytics_date_to.setDate(QDate.currentDate())
        self.analytics_date_to.setCalendarPopup(True)
        filters_layout.addWidget(self.analytics_date_to, 2, 3)
        
        # Filter buttons
        filter_btn_layout = QHBoxLayout()
        self.apply_filters_btn = QPushButton("Apply Filters")
        self.apply_filters_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; }")
        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.setStyleSheet("QPushButton { background-color: #9E9E9E; color: white; padding: 8px; }")
        filter_btn_layout.addWidget(self.apply_filters_btn)
        filter_btn_layout.addWidget(self.clear_filters_btn)
        filter_btn_layout.addStretch()
        
        filters_layout.addLayout(filter_btn_layout, 3, 0, 1, 4)
        
        layout.addWidget(filters_group)
        
        # Create splitter for analytics content
        analytics_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(analytics_splitter)
        
        # Left panel - Summary statistics
        stats_panel = QWidget()
        stats_layout = QVBoxLayout(stats_panel)
        
        # Summary metrics
        summary_group = QGroupBox("Summary Metrics")
        summary_layout = QVBoxLayout(summary_group)
        
        self.analytics_summary_text = QTextEdit()
        self.analytics_summary_text.setMaximumHeight(300)
        self.analytics_summary_text.setReadOnly(True)
        summary_layout.addWidget(self.analytics_summary_text)
        
        stats_layout.addWidget(summary_group)
        
        # Detailed breakdown table
        breakdown_group = QGroupBox("Detailed Breakdown")
        breakdown_layout = QVBoxLayout(breakdown_group)
        
        self.analytics_breakdown_table = QTableWidget()
        self.analytics_breakdown_table.setMaximumHeight(250)
        breakdown_layout.addWidget(self.analytics_breakdown_table)
        
        stats_layout.addWidget(breakdown_group)
        
        # Right panel - Charts
        charts_panel = QWidget()
        charts_layout = QVBoxLayout(charts_panel)
        charts_layout.addWidget(QLabel("Analytics Charts"))
        
        self.analytics_chart_widget = MatplotlibWidget()
        charts_layout.addWidget(self.analytics_chart_widget)
        
        analytics_splitter.addWidget(stats_panel)
        analytics_splitter.addWidget(charts_panel)
        analytics_splitter.setSizes([400, 800])
        
        self.tabs.addTab(analytics_widget, "Analytics")
        
    def setup_settings_tab(self):
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # Export settings
        export_group = QGroupBox("Export Settings")
        export_layout = QVBoxLayout(export_group)
        
        self.export_sql_btn = QPushButton("Export Database Schema")
        self.export_results_btn = QPushButton("Export Results to CSV")
        
        export_layout.addWidget(self.export_sql_btn)
        export_layout.addWidget(self.export_results_btn)
        
        layout.addWidget(export_group)
        layout.addStretch()
        
        self.tabs.addTab(settings_widget, "Settings")
        
    def setup_connections(self):
        # File operations
        self.load_file_btn.clicked.connect(self.load_file)
        
        # Analysis
        self.analyze_btn.clicked.connect(self.analyze_data)
        self.save_btn.clicked.connect(self.save_analysis)
        
        # Settings changes
        self.test_type_combo.currentTextChanged.connect(self.on_test_type_changed)
        self.trigger_current_spin.valueChanged.connect(self.update_chart)
        self.zoom_start_spin.valueChanged.connect(self.update_chart)
        self.zoom_end_spin.valueChanged.connect(self.update_chart)
        
        # Database
        self.test_connection_btn.clicked.connect(self.test_db_connection)
        self.refresh_btn.clicked.connect(self.refresh_results)
        
        # Analytics connections
        self.apply_filters_btn.clicked.connect(self.update_analytics)
        self.clear_filters_btn.clicked.connect(self.clear_analytics_filters)
        
        # Export
        self.export_sql_btn.clicked.connect(self.export_schema)
        self.export_results_btn.clicked.connect(self.export_results)
        
    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Oscilloscope CSV File", 
            "", 
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.file_label.setText(f"Loaded: {os.path.basename(file_path)}")
            self.current_file_path = file_path
            self.analyze_btn.setEnabled(True)
            
    def analyze_data(self):
        if not hasattr(self, 'current_file_path') or not self.current_file_path:
            QMessageBox.warning(self, "Warning", "Please load a CSV file first.")
            return
            
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start analysis in separate thread
        self.analysis_worker = AnalysisWorker(
            self.current_file_path, 
            self.trigger_current_spin.value()
        )
        self.analysis_worker.progress.connect(self.progress_bar.setValue)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.start()
        
    def on_analysis_finished(self, analysis_data):
        self.progress_bar.setVisible(False)
        self.current_analysis = analysis_data
        
        if not analysis_data:
            QMessageBox.critical(self, "Error", "Failed to analyze data.")
            return
            
        # Update results display
        self.update_results_display()
        self.update_chart()
        self.save_btn.setEnabled(True)
        
    def update_results_display(self):
        if not self.current_analysis:
            return
            
        # Extract analysis data
        ch1 = self.current_analysis.get('ch1', {})
        ch2 = self.current_analysis.get('ch2', {})
        trigger = self.current_analysis.get('trigger', {})
        metadata = self.current_analysis.get('metadata', {})
        
        # Format results text
        results_text = f"""
CHANNEL 1 (Voltage):
  Peak-to-Peak: {ch1.get('peak_to_peak', 0):.3f} mV
  Min/Max: {ch1.get('min', 0):.3f} / {ch1.get('max', 0):.3f} V
  RMS: {ch1.get('rms', 0):.3f} V
  Noise: {ch1.get('noise', 0):.3f} mV
  Ringdown: {ch1.get('ringdown', {}).get('ringdown_voltage', 0):.3f} mV

CHANNEL 2 (Current):
  Peak-to-Peak: {ch2.get('peak_to_peak', 0):.3f} A
  Min/Max: {ch2.get('min', 0):.3f} / {ch2.get('max', 0):.3f} A
  RMS: {ch2.get('rms', 0):.3f} A

TRIGGER ANALYSIS:
  Threshold: {trigger.get('threshold', 0):.1f} A
  Events: {trigger.get('count', 0)}

METADATA:
  Data Points: {metadata.get('data_points', 0)}
  Sample Rate: {metadata.get('sample_rate', 0):.1f} Hz
  Duration: {metadata.get('duration', 0):.3f} ms
        """
        
        self.results_text.setText(results_text.strip())
        
        # Evaluate pass/fail
        pass_fail_result = self.evaluate_pass_fail()
        
        if pass_fail_result['overall'] == 'pass':
            self.pass_fail_label.setText("Status: PASS ✓")
            self.pass_fail_label.setStyleSheet(
                "QLabel { background-color: #4CAF50; color: white; font-size: 16px; font-weight: bold; padding: 8px; }"
            )
        else:
            self.pass_fail_label.setText("Status: FAIL ✗")
            self.pass_fail_label.setStyleSheet(
                "QLabel { background-color: #F44336; color: white; font-size: 16px; font-weight: bold; padding: 8px; }"
            )
            
    def evaluate_pass_fail(self):
        if not self.current_analysis:
            return {'overall': 'unknown', 'details': {}}
            
        ch1 = self.current_analysis.get('ch1', {})
        
        # Get criteria values
        peak_lsl = self.peak_lsl_spin.value()
        peak_usl = self.peak_usl_spin.value()
        trigger_lsl = self.trigger_lsl_spin.value()
        trigger_usl = self.trigger_usl_spin.value()
        noise_lsl = self.noise_lsl_spin.value()
        noise_usl = self.noise_usl_spin.value()
        
        # Evaluate criteria
        results = {
            'peak_to_peak': peak_lsl <= ch1.get('peak_to_peak', 0) <= peak_usl,
            'trigger_current': trigger_lsl <= self.trigger_current_spin.value() <= trigger_usl,
            'noise': noise_lsl <= ch1.get('noise', 0) <= noise_usl
        }
        
        # Add ringdown check for DC02
        if self.test_type_configs[self.test_type_combo.currentText()].get('has_ringdown', False):
            ringdown_lsl = self.ringdown_lsl_spin.value()
            ringdown_usl = self.ringdown_usl_spin.value()
            ringdown_voltage = ch1.get('ringdown', {}).get('ringdown_voltage', 0)
            results['ringdown'] = ringdown_lsl <= ringdown_voltage <= ringdown_usl
        else:
            results['ringdown'] = True
            
        overall = 'pass' if all(results.values()) else 'fail'
        
        return {'overall': overall, 'details': results}
        
    def update_chart(self):
        if self.current_analysis:
            zoom_range = (self.zoom_start_spin.value(), self.zoom_end_spin.value())
            self.chart_widget.plot_data(
                self.current_analysis, 
                self.trigger_current_spin.value(), 
                zoom_range
            )
            
    def on_test_type_changed(self, test_type):
        # Show/hide skid plate diameter for IDOD
        is_idod = self.test_type_configs[test_type].get('has_skid_plate', False)
        self.skid_plate_combo.setVisible(is_idod)
        self.skid_plate_label.setVisible(is_idod)
        
        # Show/hide ringdown criteria for DC02
        has_ringdown = self.test_type_configs[test_type].get('has_ringdown', False)
        # Note: You might need to implement showing/hiding the ringdown row
        
    def save_analysis(self):
        if not self.current_analysis:
            QMessageBox.warning(self, "Warning", "No analysis data to save.")
            return
            
        # Validate required fields
        required_fields = [
            (self.test_number_edit, "Test Number"),
            (self.test_bench_edit, "Test Bench"),
            (self.tester_id_edit, "Tester ID")
        ]
        
        missing_fields = []
        for field, name in required_fields:
            if not field.text().strip():
                missing_fields.append(name)
                
        if missing_fields:
            QMessageBox.warning(
                self, 
                "Missing Fields", 
                f"Please fill in the following required fields:\n{', '.join(missing_fields)}"
            )
            return
            
        # Prepare data for database
        ch1 = self.current_analysis.get('ch1', {})
        ch2 = self.current_analysis.get('ch2', {})
        trigger = self.current_analysis.get('trigger', {})
        metadata = self.current_analysis.get('metadata', {})
        pass_fail_result = self.evaluate_pass_fail()
        
        data = {
            'file_name': os.path.basename(self.current_file_path),
            'test_number': self.test_number_edit.text(),
            'test_bench': self.test_bench_edit.text(),
            'tester_id': self.tester_id_edit.text(),
            'test_date': datetime.now().date(),
            'analysis_date': datetime.now(),
            'dut_device': self.test_type_configs[self.test_type_combo.currentText()]['dut_label'],
            'reference_device': self.test_type_configs[self.test_type_combo.currentText()]['reference_label'],
            'test_function': self.test_function_combo.currentText(),
            'peak_to_peak_mv': ch1.get('peak_to_peak', 0),
            'trigger_current_a': self.trigger_current_spin.value(),
            'noise_mv': ch1.get('noise', 0),
            'frequency_khz': metadata.get('sample_rate', 0) / 1000,
            'data_points': metadata.get('data_points', 0),
            'sample_rate_khz': metadata.get('sample_rate', 0) / 1000,
            'peak_to_peak_lsl': self.peak_lsl_spin.value(),
            'peak_to_peak_usl': self.peak_usl_spin.value(),
            'trigger_current_lsl': self.trigger_lsl_spin.value(),
            'trigger_current_usl': self.trigger_usl_spin.value(),
            'noise_lsl': self.noise_lsl_spin.value(),
            'noise_usl': self.noise_usl_spin.value(),
            'trigger_events': trigger.get('count', 0),
            'pass_fail': pass_fail_result['overall']
        }
        
        # Add optional fields
        test_type = self.test_type_combo.currentText()
        if self.test_type_configs[test_type].get('has_ringdown', False):
            data['ringdown_voltage_mv'] = ch1.get('ringdown', {}).get('ringdown_voltage', 0)
            data['ringdown_lsl'] = self.ringdown_lsl_spin.value()
            data['ringdown_usl'] = self.ringdown_usl_spin.value()
            
        if self.test_type_configs[test_type].get('has_skid_plate', False):
            data['skid_plate_diameter'] = self.skid_plate_combo.currentText()
            
        # Save to database
        if self.db_manager.save_analysis(test_type, data):
            QMessageBox.information(
                self, 
                "Success", 
                f"Analysis saved successfully!\nResult: {pass_fail_result['overall'].upper()}"
            )
            self.refresh_results()
            # Only update analytics if analytics widgets exist
            try:
                self.update_analytics()
            except AttributeError:
                pass  # Analytics tab not initialized yet
        else:
            QMessageBox.critical(self, "Error", "Failed to save analysis to database.")
            
    def test_db_connection(self):
        # Update connection parameters
        self.db_manager.connection_params.update({
            'host': self.db_host_edit.text(),
            'port': self.db_port_edit.text(),
            'database': self.db_name_edit.text(),
            'user': self.db_user_edit.text(),
            'password': self.db_password_edit.text()
        })
        
        conn = self.db_manager.connect()
        if conn:
            conn.close()
            QMessageBox.information(self, "Success", "Database connection successful!")
        else:
            QMessageBox.critical(self, "Error", "Failed to connect to database.")
            
    def refresh_results(self):
        test_type = self.filter_combo.currentText()
        if test_type == 'All':
            results = self.db_manager.get_all_results()
        else:
            results = self.db_manager.get_results(test_type)
            
        # Update table
        if results:
            self.results_table.setRowCount(len(results))
            self.results_table.setColumnCount(len(results[0]))
            self.results_table.setHorizontalHeaderLabels(list(results[0].keys()))
            
            for row, result in enumerate(results):
                for col, (key, value) in enumerate(result.items()):
                    item = QTableWidgetItem(str(value))
                    self.results_table.setItem(row, col, item)
            
            # Auto-resize columns
            self.results_table.resizeColumnsToContents()
        else:
            self.results_table.setRowCount(0)
    
    def update_analytics(self):
        """Update analytics tab with current filters"""
        try:
            filters = self.get_analytics_filters()
            summary_data = self.db_manager.get_analytics_summary(filters)
            
            if not summary_data:
                self.analytics_summary_text.setText("No data available with current filters.")
                self.analytics_breakdown_table.setRowCount(0)
                self.analytics_chart_widget.plot_analytics_charts({})
                return
            
            # Update summary text
            summary = summary_data.get('summary', {})
            test_types = summary_data.get('test_types', {})
            testers = summary_data.get('testers', {})
            test_benches = summary_data.get('test_benches', {})
            parameters = summary_data.get('parameters', {})
            
            summary_text = f"""
OVERALL SUMMARY:
  Total Tests: {summary.get('total_tests', 0)}
  Pass Count: {summary.get('pass_count', 0)}
  Fail Count: {summary.get('fail_count', 0)}
  Overall Pass Rate: {summary.get('pass_rate', 0):.1f}%
  Recent Pass Rate (30 days): {summary.get('recent_pass_rate', 0):.1f}%
  Recent Tests: {summary.get('recent_tests', 0)}

PARAMETER STATISTICS:
  Peak-to-Peak (mV):
    Mean: {parameters.get('peak_to_peak', {}).get('mean', 0):.2f}
    Std Dev: {parameters.get('peak_to_peak', {}).get('std', 0):.2f}
    Range: {parameters.get('peak_to_peak', {}).get('min', 0):.2f} - {parameters.get('peak_to_peak', {}).get('max', 0):.2f}
        
  Trigger Current (A):
    Mean: {parameters.get('trigger_current', {}).get('mean', 0):.2f}
    Std Dev: {parameters.get('trigger_current', {}).get('std', 0):.2f}
    Range: {parameters.get('trigger_current', {}).get('min', 0):.2f} - {parameters.get('trigger_current', {}).get('max', 0):.2f}
        
  Noise (mV):
    Mean: {parameters.get('noise', {}).get('mean', 0):.2f}
    Std Dev: {parameters.get('noise', {}).get('std', 0):.2f}
    Range: {parameters.get('noise', {}).get('min', 0):.2f} - {parameters.get('noise', {}).get('max', 0):.2f}
            """
            
            self.analytics_summary_text.setText(summary_text.strip())
            
            # Update breakdown table
            breakdown_data = []
            
            # Add test type breakdown
            for test_type, stats in test_types.items():
                pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
                breakdown_data.append({
                    'Category': 'Test Type',
                    'Name': test_type,
                    'Total Tests': stats['total'],
                    'Pass': stats['pass'],
                    'Fail': stats['fail'],
                    'Pass Rate (%)': f"{pass_rate:.1f}"
                })
            
            # Add tester breakdown
            for tester, stats in testers.items():
                pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
                breakdown_data.append({
                    'Category': 'Tester',
                    'Name': tester,
                    'Total Tests': stats['total'],
                    'Pass': stats['pass'],
                    'Fail': stats['fail'],
                    'Pass Rate (%)': f"{pass_rate:.1f}"
                })
            
            # Add test bench breakdown
            for bench, stats in test_benches.items():
                pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
                breakdown_data.append({
                    'Category': 'Test Bench',
                    'Name': bench,
                    'Total Tests': stats['total'],
                    'Pass': stats['pass'],
                    'Fail': stats['fail'],
                    'Pass Rate (%)': f"{pass_rate:.1f}"
                })
            
            if breakdown_data:
                self.analytics_breakdown_table.setRowCount(len(breakdown_data))
                self.analytics_breakdown_table.setColumnCount(len(breakdown_data[0]))
                self.analytics_breakdown_table.setHorizontalHeaderLabels(list(breakdown_data[0].keys()))
                
                for row, data_row in enumerate(breakdown_data):
                    for col, (key, value) in enumerate(data_row.items()):
                        item = QTableWidgetItem(str(value))
                        self.analytics_breakdown_table.setItem(row, col, item)
                
                self.analytics_breakdown_table.resizeColumnsToContents()
            
            # Update charts
            self.analytics_chart_widget.plot_analytics_charts(summary_data)
            
        except Exception as e:
            print(f"Analytics update error: {e}")
    
    def get_analytics_filters(self):
        """Get current analytics filters"""
        filters = {}
        
        if self.analytics_test_type_combo.currentText() != 'All':
            filters['test_type'] = self.analytics_test_type_combo.currentText()
        
        if self.analytics_pass_fail_combo.currentText() != 'All':
            filters['pass_fail'] = self.analytics_pass_fail_combo.currentText()
        
        if self.analytics_tester_edit.text().strip():
            filters['tester_id'] = self.analytics_tester_edit.text().strip()
        
        if self.analytics_bench_edit.text().strip():
            filters['test_bench'] = self.analytics_bench_edit.text().strip()
        
        # Fix the date conversion issue - use getDate() method
        try:
            date_from = self.analytics_date_from.date()
            date_to = self.analytics_date_to.date()
            
            # Convert QDate to Python date
            filters['date_from'] = datetime(date_from.year(), date_from.month(), date_from.day()).date()
            filters['date_to'] = datetime(date_to.year(), date_to.month(), date_to.day()).date()
        except AttributeError:
            # Fallback for different PyQt6 versions
            import datetime as dt
            filters['date_from'] = dt.date.today() - timedelta(days=30)
            filters['date_to'] = dt.date.today()
        
        return filters
    
    def clear_analytics_filters(self):
        """Clear all analytics filters"""
        self.analytics_test_type_combo.setCurrentText('All')
        self.analytics_pass_fail_combo.setCurrentText('All')
        self.analytics_tester_edit.clear()
        self.analytics_bench_edit.clear()
        self.analytics_date_from.setDate(QDate.currentDate().addDays(-30))
        self.analytics_date_to.setDate(QDate.currentDate())
        self.update_analytics()
            
    def export_schema(self):
        schema_sql = self.generate_database_schema()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Database Schema", 
            "oscilloscope_schema.sql", 
            "SQL Files (*.sql);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(schema_sql)
            QMessageBox.information(self, "Success", f"Schema exported to {file_path}")
            
    def export_results(self):
        """Export filtered results to CSV"""
        try:
            # Get current filters if on analytics tab, otherwise get all results
            if self.tabs.currentIndex() == 2:  # Analytics tab
                filters = self.get_analytics_filters()
                results = self.db_manager.get_all_results(filters)
                default_filename = f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                test_type = self.filter_combo.currentText()
                if test_type == 'All':
                    results = self.db_manager.get_all_results()
                else:
                    results = self.db_manager.get_results(test_type)
                default_filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            if not results:
                QMessageBox.warning(self, "Warning", "No data to export.")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Results to CSV", 
                default_filename, 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                # Create DataFrame and export
                df = pd.DataFrame(results)
                
                # Remove internal columns
                columns_to_remove = ['source_table']
                for col in columns_to_remove:
                    if col in df.columns:
                        df = df.drop(columns=[col])
                
                # Export to CSV
                df.to_csv(file_path, index=False)
                
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Results exported successfully!\nFile: {file_path}\nRecords: {len(results)}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")
        
    def generate_database_schema(self):
        return """-- Oscilloscope Analysis Database Schema
-- Run this in PostgreSQL to create the required tables

-- DTT Analysis Table
CREATE TABLE IF NOT EXISTS dtt_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DC02 Analysis Table (includes ringdown)
CREATE TABLE IF NOT EXISTS dc02_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    ringdown_voltage_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    ringdown_lsl DECIMAL(10,3),
    ringdown_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DTR Analysis Table
CREATE TABLE IF NOT EXISTS dtr_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- DC03 Skid Analysis Table
CREATE TABLE IF NOT EXISTS dc03_skid_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- IDOD Analysis Table (includes skid plate diameter)
CREATE TABLE IF NOT EXISTS idod_analysis (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    test_bench VARCHAR(100) NOT NULL,
    tester_id VARCHAR(50) NOT NULL,
    test_date DATE NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dut_device VARCHAR(255),
    reference_device VARCHAR(255),
    skid_plate_diameter VARCHAR(50),
    test_function VARCHAR(100),
    peak_to_peak_mv DECIMAL(10,3),
    trigger_current_a DECIMAL(10,3),
    noise_mv DECIMAL(10,3),
    frequency_khz DECIMAL(10,3),
    data_points INTEGER,
    sample_rate_khz DECIMAL(10,3),
    peak_to_peak_lsl DECIMAL(10,3),
    peak_to_peak_usl DECIMAL(10,3),
    trigger_current_lsl DECIMAL(10,3),
    trigger_current_usl DECIMAL(10,3),
    noise_lsl DECIMAL(10,3),
    noise_usl DECIMAL(10,3),
    trigger_events INTEGER,
    pass_fail VARCHAR(10)
);

-- Insert some sample data for testing
INSERT INTO dtt_analysis (
    file_name, test_number, test_bench, tester_id, test_date, test_function,
    dut_device, reference_device, peak_to_peak_mv, trigger_current_a, noise_mv,
    frequency_khz, data_points, sample_rate_khz, peak_to_peak_lsl, peak_to_peak_usl,
    trigger_current_lsl, trigger_current_usl, noise_lsl, noise_usl, trigger_events, pass_fail
) VALUES (
    'sample_test.csv', 'T001', 'Bench A', 'admin', CURRENT_DATE, 'Performance test',
    'DTT (SV/33053/0020) [DUT]', 'DTR (SV/33053/0031) [Reference]', 350.5, 55.2, 2.1,
    250.0, 2000, 250.0, 150, 400, 30, 80, 0, 5, 3, 'pass'
);"""

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set dark theme
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark_palette)
    
    # Create and show main window
    window = OscilloscopeAnalyzer()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()