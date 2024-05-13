import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps, ImageSequence
import requests
import io
import imageio

root = tk.Tk()
root.title("PSA Generator")

loading_frame = None
search_entry = None
card_number_entry = None
canvas = None
collection_page = None

FONT_BOLD = ("Segoe UI", 12, "bold")
FONT_NORMAL = ("Segoe UI", 10)

PRIMARY_COLOR = "#2196F3"
SECONDARY_COLOR = "#FF5252"
BACKGROUND_COLOR = "#F5F5F5"
HIGHLIGHT_COLOR = "#64B5F6"

max_pages = 1
collection_page = None
current_page = 1
page_size = 10
results = []

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", foreground="white", font=FONT_BOLD)
style.map("TButton", background=[("active", SECONDARY_COLOR)])
style.configure("TLabel", font=FONT_NORMAL, foreground=PRIMARY_COLOR, background=BACKGROUND_COLOR)
style.configure("TLabelframe.Label", font=FONT_BOLD, foreground=PRIMARY_COLOR, background=BACKGROUND_COLOR)
style.configure("TCombobox", font=FONT_NORMAL, selectbackground=PRIMARY_COLOR)
style.map("TCombobox", fieldbackground=[("readonly", "white")])
style.configure("TEntry", font=FONT_NORMAL)
style.configure("TFrame", background=BACKGROUND_COLOR)

search_var = tk.StringVar()
search_entry = ttk.Entry(root, textvariable=search_var, font=FONT_NORMAL)
search_entry.pack(side=tk.TOP, padx=10, pady=10)
search_entry.bind("<Return>", lambda event: search_and_display())

card_number_var = tk.StringVar()
card_number_entry = ttk.Entry(root, textvariable=card_number_var, font=FONT_NORMAL)
card_number_entry.pack(side=tk.TOP, padx=10, pady=10)
card_number_entry.bind("<Return>", lambda event: search_and_display())

canvas = tk.Canvas(root, width=600, height=400, background=BACKGROUND_COLOR)
canvas.pack(padx=10, pady=10)

page_size_var = tk.StringVar(value=page_size)
page_size_dropdown = ttk.Combobox(root, textvariable=page_size_var, values=[10, 15, 20, 50], state="readonly", font=FONT_NORMAL)
page_size_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
page_size_dropdown.bind("<<ComboboxSelected>>", lambda event: search_and_display())

page_var = tk.StringVar(value=current_page)
page_label = ttk.Label(root, text=f"Page {current_page} of {current_page}", font=FONT_NORMAL, foreground=PRIMARY_COLOR, background=BACKGROUND_COLOR)
page_label.pack(side=tk.RIGHT, padx=5, pady=5)

page_dropdown = ttk.Combobox(root, textvariable=page_var, values=list(range(1, current_page + 1)), state="readonly", font=FONT_NORMAL)
page_dropdown.pack(side=tk.RIGHT, padx=5, pady=5)
page_dropdown.bind("<<ComboboxSelected>>", lambda event: search_and_display())

def show_main_elements():
    search_entry.pack(side=tk.TOP, padx=10, pady=10)
    card_number_entry.pack(side=tk.TOP, padx=10, pady=10)
    canvas.pack(padx=10, pady=10)
    page_size_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
    page_label.pack(side=tk.RIGHT, padx=5, pady=5)
    page_dropdown.pack(side=tk.RIGHT, padx=5, pady=5)

def hide_main_elements():
    search_entry.pack_forget()
    card_number_entry.pack_forget()
    canvas.pack_forget()
    page_size_dropdown.pack_forget()
    page_label.pack_forget()
    page_dropdown.pack_forget()
    
def show_loading_screen():
    loading_frame = ttk.Frame(root)
    loading_frame.place(relx=0.5, rely=0.5, anchor="center")

    style = ttk.Style()
    style.configure("TFrame", background=BACKGROUND_COLOR)

    loading_gif_path = "C:/PROJECTS/PSAGenerator/giphy.gif"
    loading_label = ImageLabel(loading_frame)
    loading_label.pack()

    loading_label.load_gif(loading_gif_path)
    loading_label.start_animation()

    loading_text = ttk.Label(loading_frame, text="Loading Cards...", font=FONT_BOLD, foreground=PRIMARY_COLOR)
    loading_text.pack()

    return loading_frame

def search_and_display():
    global current_page, page_size, max_pages, results, loading_frame

    loading_frame = show_loading_screen()

    hide_main_elements()

    pokemon_name = search_var.get()
    card_number = card_number_var.get()
    pokemon_results = search_pokemon_by_name_and_number(pokemon_name, card_number, current_page, page_size)

    if pokemon_results:
        max_pages = (len(pokemon_results) + page_size - 1) // page_size

        root.after(1000, lambda: display_results_in_gui(pokemon_results, current_page, max_pages, page_size, loading_frame))
    else:
        display_results_in_gui([], current_page, max_pages, page_size, loading_frame)

class ImageLabel(tk.Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.card_id = None

    def set_card_id(self, card_id):
        self.card_id = card_id

    def get_card_id(self):
        return self.card_id

    def load_gif(self, gif_path):
        self.stop_animation()

        self.frames = []
        try:
            gif = Image.open(gif_path)
            for frame in ImageSequence.Iterator(gif):
                resized_frame = frame.resize((100, 100), Image.BICUBIC)
                frame_data = ImageTk.PhotoImage(resized_frame)
                self.frames.append(frame_data)
        except Exception as e:
            print(f"Error loading gif: {e}")
            return

        self.delay = gif.info.get("duration", 100)
        if self.frames:
            self.start_animation()

    def start_animation(self, frame_index=0):
        self.next_frame(frame_index)

    def stop_animation(self):
        if hasattr(self, "after_id"):
            self.after_cancel(self.after_id)

    def next_frame(self, frame_index):
        if self.frames:
            self.config(image=self.frames[frame_index])
            self.after_id = self.after(self.delay, lambda: self.next_frame((frame_index + 1) % len(self.frames)))

class CollectionPage(tk.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection_data = []

        self.create_widgets()

    def update_display(self):
        self.collection_tree.delete(*self.collection_tree.get_children())
        for index, card_id in enumerate(self.collection_data, start=1):
            card_info = requests.get(f"https://api.pokemontcg.io/v2/cards/{card_id}").json()
            name = card_info.get("name", "")
            release_date = card_info.get("set", {}).get("releaseDate", "")
            number = card_info.get("number", "")
            large

            _image_url = card_info.get("images", {}).get("large", "")
            image_data = requests.get(large_image_url).content

            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((100, 100), Image.BICUBIC)
            photo = ImageTk.PhotoImage(img)

            self.collection_tree.insert("", "end", values=(index, card_id, name, photo, release_date, number))
            self.collection_tree.image = photo
    
    def create_widgets(self):
        arrow_image = Image.open("arrow_icon.png")
        arrow_image = arrow_image.resize((20, 20), Image.BICUBIC)
        arrow_icon = ImageTk.PhotoImage(arrow_image)

        self.home_arrow = tk.Button(self, image=arrow_icon, bg=BACKGROUND_COLOR, command=self.show_home_page)
        self.home_arrow.image = arrow_icon
        self.home_arrow.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        self.collection_tree = ttk.Treeview(self, columns=("ID", "Name", "Image", "Release Date", "Number"))
        self.collection_tree.heading("#0", text="Index")
        self.collection_tree.heading("ID", text="ID")
        self.collection_tree.heading("Name", text="Name")
        self.collection_tree.heading("Image", text="Image")
        self.collection_tree.heading("Release Date", text="Release Date")
        self.collection_tree.heading("Number", text="Number")

        self.collection_tree.column("#0", width=50)
        self.collection_tree.column("ID", width=100)
        self.collection_tree.column("Name", width=150)
        self.collection_tree.column("Image", width=150)
        self.collection_tree.column("Release Date", width=150)
        self.collection_tree.column("Number", width=100)

        self.collection_tree.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    def show_home_page(self):
        self.pack_forget()

class Toast(tk.Toplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("Toast")
        self.geometry("+%d+%d" % (parent.winfo_x() + parent.winfo_width() // 2, parent.winfo_y() + parent.winfo_height() - 40))
        self.configure(bg=BACKGROUND_COLOR)
        
        label = ttk.Label(self, text=message, font=FONT_NORMAL, background=PRIMARY_COLOR, foreground="white", padding=(10, 5))
        label.pack()

        self.after(2000, self.destroy)

def save_to_collection(image_label):
    global collection_page

    if collection_page is not None:
        card_id = image_label.get_card_id()
        if card_id not in collection_page.collection_data:
            collection_page.collection_data.append(card_id)
            toast = Toast(root, f"{card_id} saved to collection.")
            update_display()
        else:
            toast = Toast(root, f"{card_id} is already in the collection.")
    else:
        print("Error: collection_page is not initialized.")

def show_collection_page():
    global collection_page
    collection_page = CollectionPage(root, width=600, height=400, background=BACKGROUND_COLOR)
    collection_page.pack(padx=10, pady=10)
    hide_main_elements()

def show_collection():
    show_collection_page()

def search_pokemon(query, page=1, page_size=10):
    base_url = "https://api.pokemontcg.io/v2/cards"
    params = {
        'q': query,
        'pageSize': page_size,
        'page': page
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        results = response.json().get("data", [])
        return results
    else:
        return None

def search_pokemon_by_name_and_number(pokemon_name, card_number=None, page=1, page_size=10):
    query = f'name:{pokemon_name}'
    if card_number:
        try:
            x, y = map(int, card_number.split('/'))
        except ValueError:
            print(f"Invalid card number format: {card_number}")
            return None

        query += f' number:{x}'
        query += f' set.printedTotal:{y}'

    print(f"Query: {query}")
    
    results = search_pokemon(query, page, page_size)
    
    print(f"Results: {results}")

    return results

def display_results_in_gui(search_results, current_page, max_pages, page_size, loading_frame=None):
    global results

    if not search_results:
        print("No results found.")
        return

    results = search_results

    update_display()

def get_image_label_by_card_id(card_id):
    for widget in canvas.winfo_children():
        if isinstance(widget, ImageLabel) and widget.get_card_id() == card_id:
            return widget
    return None

def on_image_click(card_id):
    selected_card = requests.get(f"https://api.pokemontcg.io/v2/cards/{card_id}").json()
    print(f"\nFull information for selected card (ID: {card_id}):")
    print(selected_card)

    image_label = get_image_label_by_card_id(card_id)

    if image_label:
        save_to_collection(image_label)

        for widget in canvas.winfo_children():
            if isinstance(widget, ImageLabel):
                if widget.get_card_id() == card_id:
                    widget.configure(borderwidth=2, relief="solid", highlightbackground=HIGHLIGHT_COLOR)
                else:
                    widget.configure(borderwidth=0, relief="flat", highlightbackground=BACKGROUND_COLOR)

def update_display():
    global current_page, page_size, results, collection_page

    page_label.config(text=f"Page {current_page} of {max_pages}")

    for widget in canvas.winfo_children():
        widget.destroy()

    for index, result in enumerate(results, 1):
        card_id = result.get("id", "")
        if not card_id:
            continue

        images = result.get("images", {})
        large_image_url = images.get("large", "")
        if not large_image_url:
            continue

        try:
            image_data = requests.get(large_image_url).content
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((100, 100), Image.BICUBIC)
            photo = ImageTk.PhotoImage(img)

            on_click = lambda card_id=card_id: on_image_click(card_id)

            label = ImageLabel(canvas, image=photo, cursor="hand2", bg=BACKGROUND_COLOR)
            label.image = photo
            label.set_card_id(card_id)
            label.grid(row=(index - 1) // 5, column=(index - 1) % 5, padx=5, pady=5, sticky="nsew")
            label.bind("<Button-1>", lambda event, card_id=card_id: on_image_click(card_id))
        except Exception as e:
            print(f"Error loading image for card {card_id}: {e}")

    if collection_page:
        collection_page.update_display()

    if loading_frame:
        loading_frame.destroy()

    show_main_elements()

def on_page_change(new_page, *args):
    global current_page
    current_page = new_page
    update_display()

def on_page_size_change(*

args):
    global page_size
    page_size = int(page_size_var.get())
    update_display()

def on_search(*args):
    global current_page
    current_page = 1
    update_display()

book_image = Image.open("book_icon.png")
book_image = book_image.resize((20, 20), Image.BICUBIC)
book_icon = ImageTk.PhotoImage(book_image)

book_button = tk.Button(root, image=book_icon, bg=BACKGROUND_COLOR, command=show_collection)
book_button.image = book_icon
book_button.place(relx=0.95, rely=0.02, anchor="ne")

update_display()

root.configure(bg=BACKGROUND_COLOR)

root.mainloop()
