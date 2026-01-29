import sys  # Needed to handle command-line arguments and exit the application
from functools import lru_cache  # Used to memoize the dynamic programming function for speed
from itertools import combinations  # Used to generate all subsets of appliances for optimization
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

INF = float("inf")


# -------------------------------
# Core Algorithm
# -------------------------------

class Appliance:
    def __init__(self, name, power, duration, start, end):
        self.name = name
        self.power = power
        self.duration = duration
        self.start = start
        self.end = end


class EnergyScheduler:
    def __init__(self, appliances, prices, max_load):
        self.appliances = appliances
        self.prices = prices
        self.max_load = max_load
        self.T = len(prices)
        self.n = len(appliances)

    def feasible_subset(self, t, remaining, subset):
        load = 0
        for i in subset:
            app = self.appliances[i]
            if remaining[i] <= 0:
                return False
            if not (app.start <= t <= app.end - remaining[i]):
                return False
            load += app.power
        return load <= self.max_load

    def solve(self):
        start_remaining = tuple(app.duration for app in self.appliances)

        @lru_cache(None)
        def dp(t, remaining):
            if t == self.T:
                return 0 if all(r == 0 for r in remaining) else INF
            best_cost = INF
            for k in range(self.n + 1):
                for subset in combinations(range(self.n), k):
                    if not self.feasible_subset(t, remaining, subset):
                        continue
                    load = sum(self.appliances[i].power for i in subset)
                    cost = load * self.prices[t]
                    next_remaining = list(remaining)
                    for i in subset:
                        next_remaining[i] -= 1
                    best_cost = min(
                        best_cost,
                        cost + dp(t + 1, tuple(next_remaining))
                    )
            return best_cost

        schedule = [[] for _ in range(self.T)]
        remaining = start_remaining

        for t in range(self.T):
            for k in range(self.n + 1):
                for subset in combinations(range(self.n), k):
                    if not self.feasible_subset(t, remaining, subset):
                        continue
                    load = sum(self.appliances[i].power for i in subset)
                    cost = load * self.prices[t]
                    next_remaining = list(remaining)
                    for i in subset:
                        next_remaining[i] -= 1
                    if cost + dp(t + 1, tuple(next_remaining)) == dp(t, remaining):
                        schedule[t] = [self.appliances[i].name for i in subset]
                        remaining = tuple(next_remaining)
                        break
                else:
                    continue
                break
        return dp(0, start_remaining), schedule


# -------------------------------
# GUI
# -------------------------------

class EnergyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Energy Cost Optimizer")
        self.setMinimumWidth(950)

        layout = QVBoxLayout()

        # --- Max Load ---
        load_layout = QHBoxLayout()
        load_label = QLabel("Max Load (kW):")
        load_layout.addWidget(load_label)
        load_info = self.create_info_icon(
            "Maximum total power allowed at any hour.\nExample: 5.0 kW"
        )
        load_layout.addWidget(load_info)
        self.max_load_input = QLineEdit("5.0")
        load_layout.addWidget(self.max_load_input)
        layout.addLayout(load_layout)

        # --- Electricity Prices ---
        price_layout = QHBoxLayout()
        price_label = QLabel("Electricity Prices (24 comma-separated values):")
        price_layout.addWidget(price_label)
        price_info = self.create_info_icon(
            "Enter 24 hourly electricity prices (PHP/kWh) from hour 0 to 23."
        )
        price_layout.addWidget(price_info)
        layout.addLayout(price_layout)
        self.price_input = QTextEdit(
            "5,5,6,8,10,12,15,18,20,18,15,12,10,9,8,7,6,6,7,9,12,15,10,6"
        )
        layout.addWidget(self.price_input)

        # --- Appliance Table ---
        appliance_layout = QHBoxLayout()
        appliance_label = QLabel("Appliances")
        appliance_layout.addWidget(appliance_label)
        appliance_info = self.create_info_icon(
            "Add appliances with Name, Power (kW), Duration (hours), Start hour, End hour"
        )
        appliance_layout.addWidget(appliance_info)
        layout.addLayout(appliance_layout)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Power (kW)", "Duration (h)", "Start", "End"]
        )
        layout.addWidget(self.table)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Appliance")
        add_btn.setFixedWidth(120)
        add_btn.setToolTip("Click to add a new appliance row")
        add_btn.clicked.connect(self.add_appliance)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected Appliance")
        remove_btn.setFixedWidth(180)
        remove_btn.setToolTip("Select a row and click to remove the appliance")
        remove_btn.clicked.connect(self.remove_appliance)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)

        # --- Solve Button  ---
        solve_layout = QHBoxLayout()
        solve_layout.addStretch()
        solve_btn = QPushButton("Optimize Schedule")
        solve_btn.setFixedWidth(180)
        solve_btn.setToolTip("Click to run the optimization algorithm and display schedule and cost")
        solve_btn.clicked.connect(self.run_optimization)
        solve_layout.addWidget(solve_btn)
        solve_layout.addStretch()
        layout.addLayout(solve_layout)

        # --- Output ---
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)

        # Populate table with example appliances
        self.populate_example_appliances()

    def create_info_icon(self, tooltip_text):
        icon = QLabel("ℹ️")
        icon.setFixedSize(20, 20)
        icon.setStyleSheet("""
            QLabel {
                border-radius: 10px;
                background-color: #cce5ff;
                color: #004085;
                font-weight: bold;
                text-align: center;
            }
            QLabel:hover {
                background-color: #b8daff;
            }
        """)
        icon.setToolTip(tooltip_text)
        icon.setAlignment(Qt.AlignCenter)
        return icon

    def populate_example_appliances(self):
        examples = [
            ("Washing Machine", 1.5, 2, 8, 20),
            ("TV", 0.1, 5, 18, 23),
            ("Air Conditioner", 2.0, 4, 12, 22),
            ("Electric Fan", 0.05, 6, 8, 22),
            ("Phone Charger", 0.01, 3, 0, 23)
        ]
        for name, power, duration, start, end in examples:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(power)))
            self.table.setItem(row, 2, QTableWidgetItem(str(duration)))
            self.table.setItem(row, 3, QTableWidgetItem(str(start)))
            self.table.setItem(row, 4, QTableWidgetItem(str(end)))

    def add_appliance(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(5):
            self.table.setItem(row, col, QTableWidgetItem(""))

    def remove_appliance(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self, "No Selection", "Please select an appliance to remove."
            )
            return
        self.table.removeRow(selected_row)

    def run_optimization(self):
        try:
            prices = [float(x) for x in self.price_input.toPlainText().split(",")]
            if len(prices) != 24:
                raise ValueError("Exactly 24 price values are required.")

            max_load = float(self.max_load_input.text())

            appliances = []
            for row in range(self.table.rowCount()):
                name = self.table.item(row, 0).text()
                power = float(self.table.item(row, 1).text())
                duration = int(self.table.item(row, 2).text())
                start = int(self.table.item(row, 3).text())
                end = int(self.table.item(row, 4).text())

                appliances.append(Appliance(name, power, duration, start, end))

            scheduler = EnergyScheduler(appliances, prices, max_load)
            cost, schedule = scheduler.solve()

            self.output.clear()
            self.output.append("Optimal Schedule:\n")

            for hour, running in enumerate(schedule):
                if running:
                    if hour == 0:
                        display_hour = "12 AM"
                    elif 1 <= hour < 12:
                        display_hour = f"{hour} AM"
                    elif hour == 12:
                        display_hour = "12 PM"
                    else:
                        display_hour = f"{hour - 12} PM"
                    self.output.append(f"{display_hour}: {', '.join(running)}")

            self.output.append(f"\nTotal Energy Cost: PHP {cost:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

tiiiiiiiiiiiteeeeeeeeeeeeeeeeeeeeeeeeeeeee
# -------------------------------
# Run App
# -------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnergyGUI()
    window.show()
    sys.exit(app.exec_())
