##Copyright (C) 2019 Patento Kft.
##
##This program is free software: you can redistribute it and/or modify
##it under the terms of the GNU General Public License as published by
##the Free Software Foundation, either version 3 of the License, or
##(at your option) any later version.
##
##This program is distributed in the hope that it will be useful,
##but WITHOUT ANY WARRANTY; without even the implied warranty of
##MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##GNU General Public License for more details.
##
##You should have received a copy of the GNU General Public License
##along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.optimize import fsolve
from fpdf import FPDF
import tempfile
import os
import unicodedata

# Állandók
R = 8.314
M = 0.029
P = 101325

BASE_WIDTH = 800
BASE_FONT_SIZE = 10

root = tk.Tk()
root.title("Levegőkeverő számítás")
root.update_idletasks()
root.geometry("")  # Automatikus méretezés a tartalomhoz

frame = ttk.Frame(root, padding=20)
frame.grid(row=0, column=0)

calculation_result_text = ""  # PDF-be is kerülő utolsó számítási eredmény
flow_entries = []
temp_entries = []
fixed_vars = []
labels_widgets = []
all_widgets = []

font_style = font.Font(size=BASE_FONT_SIZE)

style = ttk.Style()
font_style = font.Font(size=BASE_FONT_SIZE)

columns = ["Cső #", "Térfogatáram [m³/s]", "Hőmérséklet [°C]", "Fixált?"]
for i, text in enumerate(columns):
    lbl = ttk.Label(frame, text=text)
    lbl.grid(row=0, column=i)
    lbl.configure(font=font_style)
    all_widgets.append(lbl)

row_offset = 1

def add_pipe(label="Környezeti levegő"):
    row = len(flow_entries) + row_offset
    label_widget = ttk.Label(frame, text=label if row == 1 else f"{row}. cső", font=font_style)
    label_widget.grid(row=row, column=0, padx=5, pady=5)
    flow = ttk.Entry(frame, width=10, font=font_style)
    temp = ttk.Entry(frame, width=10, font=font_style)
    fixed = tk.BooleanVar()
    check = ttk.Checkbutton(frame, variable=fixed)
    check.configure(style='Custom.TCheckbutton')
    flow.grid(row=row, column=1, padx=5)
    temp.grid(row=row, column=2, padx=5)
    check.grid(row=row, column=3, padx=5)

    flow_entries.append(flow)
    temp_entries.append(temp)
    fixed_vars.append(fixed)
    labels_widgets.append((label_widget, flow, temp, check))
    all_widgets.extend([label_widget, flow, temp, check])

add_pipe()
add_pipe()
add_pipe()

def add_row():
    add_pipe()

def remove_row():
    if len(flow_entries) > 1:
        label, flow, temp, check = labels_widgets.pop()
        label.destroy()
        flow.destroy()
        temp.destroy()
        check.destroy()
        flow_entries.pop()
        temp_entries.pop()
        fixed_vars.pop()


def calculate():
    try:
        vol_flows = []
        temps_K = []
        for flow, temp in zip(flow_entries, temp_entries):
            if flow.get() and temp.get():
                V = float(flow.get())
                T = float(temp.get()) + 273.15
                vol_flows.append(V)
                temps_K.append(T)

        if not vol_flows:
            result_label.config(text="Adj meg legalább egy cső adatot!")
            return

        if density_check_var.get():
            densities = [P * M / (R * T) for T in temps_K]
        else:
            densities = [1.2 for _ in temps_K]

        mass_flows = [rho * V for rho, V in zip(densities, vol_flows)]
        energy_contributions = [m * T for m, T in zip(mass_flows, temps_K)]

        T_mix = sum(energy_contributions) / sum(mass_flows) - 273.15
        total_V = sum(vol_flows)

        result_label.config(text=f"Keverék hőmérséklet: {T_mix:.2f} °C\nTérfogatáram egyenleg: {total_V:.2f} m³/s")

    except Exception as e:
        result_label.config(text=f"Hiba: {e}")

    global calculation_result_text
    calculation_result_text = f"Keverék hőmérséklet: {T_mix:.2f} °C\nTérfogatáram egyenleg: {total_V:.2f} m³/s"
    result_label.config(text=calculation_result_text)
    
def reverse_calculation():
    try:
        T_target = float(target_temp_entry.get()) + 273.15

        flows, temps, fixed = [], [], []
        for f, t, fx in zip(flow_entries, temp_entries, fixed_vars):
            flows.append(float(f.get()) if f.get() else None)
            temps.append(float(t.get()) + 273.15 if t.get() else None)
            fixed.append(fx.get())

        idx_missing_temp = [i for i, t in enumerate(temps) if t is None and flows[i] is not None and not fixed[i]]
        if len(idx_missing_temp) == 1:
            idx = idx_missing_temp[0]

            def equation(T_unknown):
                total_m, total_E = 0, 0
                for i in range(len(flows)):
                    if flows[i] is None:
                        continue
                    if i == idx:
                        rho = P * M / (R * T_unknown) if density_check_var.get() else 1.2
                        m = rho * flows[i]
                        total_m += m
                        total_E += m * T_unknown
                    else:
                        rho = P * M / (R * temps[i]) if density_check_var.get() else 1.2
                        m = rho * flows[i]
                        total_m += m
                        total_E += m * temps[i]
                T_mix = total_E / total_m
                return T_mix - T_target

            T_result_K = fsolve(equation, T_target)[0]
            T_result_C = T_result_K - 273.15

            result_label.config(text=f"Szükséges hőmérséklet: {T_result_C:.2f} °C")
            return

        result_label.config(text="Nincs számolható cső megadva!")

    except Exception as e:
        result_label.config(text=f"Hiba visszaszámításnál: {e}")

def show_plot():
    vol_flows = []
    temps_C = []
    for flow, temp in zip(flow_entries, temp_entries):
        if flow.get() and temp.get():
            vol_flows.append(float(flow.get()))
            temps_C.append(float(temp.get()))

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(range(len(vol_flows)), temps_C, width=0.6, color='skyblue')
    ax.set_xticks(range(len(vol_flows)))
    ax.set_xticklabels(["környezeti levegő"] + [f"{i+2}. cső" for i in range(len(vol_flows)-1)])
    ax.set_ylabel("Hőmérséklet [°C]")
    ax.set_title("Bemeneti levegő hőmérsékletek")
    for i, (bar, v) in enumerate(zip(bars, vol_flows)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, f"{v:.2f} m³/s", ha='center', va='center', fontsize=8, color='black')
    plt.tight_layout()

    plot_window = tk.Toplevel(root)
    plot_window.title("Hőmérsékletdiagram")
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.get_tk_widget().pack()
    canvas.draw()

#import unicodedata
#from fpdf import FPDF
#import matplotlib.pyplot as plt
#import tempfile

def safe_text(text):
    if not isinstance(text, str):
        text = str(text)
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

def write(pdf, text):
    pdf.cell(0, 10, safe_text(text), ln=True)


def save_temp_diagram(temp_values):
    plt.figure()
    labels = [label for label, _ in temp_values]
    temps = [float(temp) if temp != "" else 0 for _, temp in temp_values]

    bars = plt.bar(labels, temps)
    plt.title("Bejövő hőmérsékletek")
    plt.xlabel("Cső")
    plt.ylabel("Hőmérséklet [°C]")

    for bar, temp in zip(bars, temps):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                 f"{temp} °C", ha='center', va='bottom', fontsize=8)

    plt.xticks(rotation=45)
    plt.tight_layout()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name)
    plt.close()
    return temp_file.name


class CustomPDF(FPDF):
    def header(self):
        self.set_draw_color(0, 0, 0)
        self.rect(5.0, 5.0, 200.0, 287.0)  # Keret
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Levegokevero Jelentes", ln=True, align="C")
        self.ln(5)

    def add_table(self, data, col_widths):
        self.set_font("Arial", size=10)
        self.set_fill_color(200, 200, 200)

        headers = ["Cso neve", "Terfogat [m3/s]", "Homerseklet [C]"]
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, border=1, align="C", fill=True)
        self.ln()

        self.set_fill_color(245, 245, 245)
        fill = False
        for row in data:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 8, safe_text(str(item)), border=1, align="C", fill=fill)
            self.ln()
            fill = not fill
        self.ln(5)


def generate_equation_image_1(include_cp=False):
    import matplotlib.pyplot as plt
    import tempfile
    plt.figure(figsize=(6, 1))
    plt.axis('off')
    equation = r"$\sum \dot{m} \cdot "
    equation += r"c_p \cdot " if include_cp else ""
    equation += r"T = \dot{m}_{összeg} \cdot "
    equation += r"c_p \cdot " if include_cp else ""
    equation += r"T_{keverék}$"
    plt.text(0.5, 0.5, equation, ha='center', va='center', fontsize=16)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name, bbox_inches='tight', transparent=True)
    plt.close()
    return temp_file.name



def generate_equation_image_2():
    import matplotlib.pyplot as plt
    import tempfile
    plt.figure(figsize=(6, 1))
    plt.axis('off')
    plt.text(0.5, 0.5, r"$T_{keverék} = \frac{\sum \dot{m} \cdot T}{\sum \dot{m}}$", ha='center', va='center', fontsize=16)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name, bbox_inches='tight', transparent=True)
    plt.close()
    return temp_file.name



def save_air_mixer_pdf(data_summary: str):
    global calculation_result_text

    # Ábrák legenerálása
    temp_data = [(labels_widgets[i][0].cget("text"), temp_entries[i].get()) for i in range(len(temp_entries))]
    temp_chart_path = save_temp_diagram(temp_data)

    # Sűrűségdiagram generálása
    import matplotlib.pyplot as plt
    import numpy as np
    import tempfile

    P = 101325  # Pa
    M = 0.0289647  # kg/mol
    R = 8.314462618  # J/(mol·K)

    density_chart_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    density_chart_path = density_chart_file.name
    density_chart_file.close()

    plt.figure()
    temps_C = np.linspace(0, 1300, 300)
    temps_K = temps_C + 273.15
    densities = P * M / (R * temps_K)
    plt.plot(temps_C, densities, color='orange')
    plt.title("Levego suruseg valtozasa")
    plt.xlabel("Homerseklet [C]")
    plt.ylabel("Suruseg [kg/m3]")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(density_chart_path)
    plt.close()

    pdf = CustomPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Célhőmérséklet
    pdf.cell(0, 10, safe_text(f"Cel homerseklet: {target_temp_entry.get()} C"), ln=True, align="L")
    pdf.ln(5)

    # Eredmény középre kiemelve
    if calculation_result_text:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, safe_text("Szamitott eredmeny:"), ln=True, align="C")
        for line in calculation_result_text.split("\n"):
            pdf.cell(0, 10, safe_text(line), ln=True, align="C")
        pdf.ln(5)

    # Táblázat adatokkal
    table_data = []
    for i in range(len(flow_entries)):
        label_text = labels_widgets[i][0].cget("text")
        flow = flow_entries[i].get()
        temp = temp_entries[i].get()
        table_data.append([label_text, flow, temp])

    col_widths = [60, 60, 60]
    pdf.add_table(table_data, col_widths)

    # Ábrák a 2. oldalra
    pdf.add_page()
    pdf.image(temp_chart_path, x=10, y=20, w=180)
    pdf.image(density_chart_path, x=10, y=150, w=180)

    # Számítási módszer a 3. oldalra
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, "Szamitasi modszerek:", ln=True)

    pdf.cell(0, 8, "- Az energia-egyenlet alapjan:", ln=True)
    eq1 = generate_equation_image_1(include_cp=True)
    pdf.image(eq1, x=20, y=pdf.get_y() + 10, w=160)
    pdf.ln(50)

    pdf.cell(0, 8, "- Egyszerusitve:", ln=True)
    eq2 = generate_equation_image_2()
    pdf.image(eq2, x=20, y=pdf.get_y() + 10, w=160)
    pdf.ln(50)

    pdf.cell(0, 8, "- Feltetelezesek:", ln=True)
    for line in ["* cp allando", "* Levego idealis gaz", "* Surusegvaltozas figyelembe veve"]:
        pdf.cell(0, 8, safe_text(line), ln=True)

    # PDF Mentés
    pdf.output("levegokevero_jelentes.pdf")

    return "PDF mentve: levegokevero_jelentes.pdf"




def show_density_curve():
    temps_C = np.linspace(0, 1300, 300)
    temps_K = temps_C + 273.15
    densities = P * M / (R * temps_K)

    fig, ax = plt.subplots()
    ax.plot(temps_C, densities, color='orange')
    ax.set_title("Levegő sűrűség változása hőmérséklettel")
    ax.set_xlabel("Hőmérséklet [°C]")
    ax.set_ylabel("Sűrűség [kg/m³]")
    ax.grid(True)
    plt.tight_layout()

    window = tk.Toplevel(root)
    window.title("Sűrűségfüggvény")
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.get_tk_widget().pack()
    canvas.draw()


control_frame = ttk.Frame(root, padding=10)
control_frame.grid(row=1, column=0, sticky="nsew")
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)
root.columnconfigure(0, weight=1)
control_frame.columnconfigure(0, weight=1)
control_frame.columnconfigure(1, weight=1)
control_frame.columnconfigure(2, weight=1)
control_frame.columnconfigure(3, weight=1)

def show_help():
    help_text = (
        "Számítási módszer:\n"
        "- Az energia-egyenlet alapján:\n"
        "  Σṁ·cp·T = ṁₒₛₛₑg·cp·Tₖₑᵥₑᵣₑₖ\n"
        "- Egyszerűsítve:\n"
        "  Tₖₑᵥₑᵣₑₖ = Σ(ṁ·T) / Σṁ\n"
        "- Feltételezések:\n"
        "  * cp állandó\n"
        "  * Levegő ideális gáz\n"
        "  * Sűrűségváltozás figyelembe véve"
    )
    messagebox.showinfo("Segítség - Számítási módszer", help_text)

help_button = ttk.Button(control_frame, text="Help", command=show_help)
help_button.grid(row=5, column=0, columnspan=4, pady=10, sticky="ew")


add_btn = ttk.Button(control_frame, text="+ Cső hozzáadása", command=add_row)
all_widgets.append(add_btn)
add_btn.grid(row=0, column=0, padx=5, sticky="ew")

remove_btn = ttk.Button(control_frame, text="– Cső eltávolítása", command=remove_row)
all_widgets.append(remove_btn)
remove_btn.grid(row=0, column=1, padx=5, sticky="ew")

density_check_var = tk.BooleanVar(value=True)
density_check = ttk.Checkbutton(control_frame, text="Sűrűségváltozás figyelembevétele", variable=density_check_var, style='Custom.TCheckbutton')
all_widgets.append(density_check)
density_check.grid(row=0, column=2, padx=5, sticky="ew")

target_temp_label = ttk.Label(control_frame, text="Cél hőmérséklet [°C]")
target_temp_label.grid(row=1, column=0, sticky="e")
all_widgets.append(target_temp_label)
target_temp_entry = ttk.Entry(control_frame, width=10)
all_widgets.append(target_temp_entry)
target_temp_entry.grid(row=1, column=1, sticky="ew")

show_density_btn = ttk.Button(control_frame, text="Sűrűséggörbe megtekintése", command=show_density_curve)
all_widgets.append(show_density_btn)
show_density_btn.grid(row=1, column=2, columnspan=2, sticky="ew")

show_plot_btn = ttk.Button(control_frame, text="Hőmérsékletdiagram megtekintése", command=show_plot)
all_widgets.append(show_plot_btn)
show_plot_btn.grid(row=2, column=2, columnspan=2, pady=5, sticky="ew")


def generate_data_summary():
    summary_lines = []
    summary_lines.append(f"Cel homerseklet: {target_temp_entry.get()} °C")

    for i in range(len(flow_entries)):
        label_widget = labels_widgets[i][0]  # csak a label kell a tuple-ből
        label_text = label_widget.cget("text")
        flow = flow_entries[i].get()
        temp = temp_entries[i].get()
        summary_lines.append(f"{label_text}: {flow} m3/s, {temp} °C")

    return "\n".join(summary_lines)



def on_save_pdf():
    try:
        summary = generate_data_summary()  # ez összefoglalja a csövek adatait
        result = save_air_mixer_pdf(summary)
        result_label.config(text=result_label.cget("text") + f"\n{result}")
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("Hiba", f"Nem sikerült a PDF mentés.\n\n{e}")



calc_button = ttk.Button(control_frame, text="Számítás", command=calculate)
all_widgets.append(calc_button)
calc_button.grid(row=3, column=0, pady=10, sticky="ew")

reverse_button = ttk.Button(control_frame, text="Visszaszámítás", command=reverse_calculation)
all_widgets.append(reverse_button)
reverse_button.grid(row=3, column=1, pady=10, sticky="ew")

save_pdf_btn = ttk.Button(control_frame, text="Mentés PDF-be", command=on_save_pdf)
save_pdf_btn.grid(row=3, column=2, columnspan=2, pady=10, sticky="ew")



result_label = ttk.Label(control_frame, text="")
all_widgets.append(result_label)
result_label.grid(row=4, column=0, columnspan=4, pady=10, sticky="ew")




root.mainloop()
