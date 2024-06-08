import base64
import sqlite3
import warnings
from io import BytesIO
from typing import Union

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Ignore the FutureWarning about passing arguments to Accelerator
warnings.filterwarnings(
    "ignore",
    "DataFrame.applymap has been deprecated. Use DataFrame.map instead.",
    category=FutureWarning,
    append=True,
)


# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS boxes (
                 id INTEGER PRIMARY KEY,
                 box_identifier TEXT NOT NULL,
                 location TEXT NOT NULL)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS items (
                 id INTEGER PRIMARY KEY,
                 box_id INTEGER NOT NULL,
                 name TEXT NOT NULL,
                 category TEXT NOT NULL,
                 description TEXT,
                 price REAL,
                 image TEXT,
                 FOREIGN KEY(box_id) REFERENCES boxes(id))"""
    )
    conn.commit()
    conn.close()


# Fetch boxes from database
def fetch_boxes():
    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query("SELECT * FROM boxes", conn)
    conn.close()
    return df


# Fetch items from database
def fetch_items(box_id):
    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query(f"SELECT * FROM items WHERE box_id={box_id}", conn)
    conn.close()
    return df


# Insert a new box
def insert_box(box_identifier, location):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO boxes (box_identifier, location) VALUES (?, ?)",
        (box_identifier, location),
    )
    conn.commit()
    conn.close()


# Insert a new item
def insert_item(
    box_id: int,
    name: str,
    category: str,
    description: str,
    price: float,
    image: Union[bytes, None],
):
    # Convert image to base64
    if image is not None:
        image = base64.b64encode(image).decode("utf-8")

    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO items (box_id, name, category, description, price, image) VALUES (?, ?, ?, ?, ?, ?)",
        (box_id, name, category, description, price, image),
    )
    conn.commit()
    conn.close()


# Update a box
def update_box(box_id, box_identifier, location):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute(
        "UPDATE boxes SET box_identifier=?, location=? WHERE id=?",
        (box_identifier, location, box_id),
    )
    conn.commit()
    conn.close()


# Update an item
def update_item(item_id, name, category, description, price, image):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute(
        "UPDATE items SET name=?, category=?, description=?, price=?, image=? WHERE id=?",
        (name, category, description, price, image, item_id),
    )
    conn.commit()
    conn.close()


# Delete a box
def delete_box(box_id):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("DELETE FROM boxes WHERE id=?", (box_id,))
    conn.commit()
    conn.close()


# Delete an item
def delete_item(item_id):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# Streamlit App
def main():
    st.title("Inventory Management System")

    # Initialize database
    init_db()

    # Display and manage boxes
    st.header("Boxes")
    box_df = fetch_boxes()

    gb = GridOptionsBuilder.from_dataframe(box_df)
    gb.configure_pagination()
    gb.configure_columns(["id"], hide=True)
    gb.configure_column("box_identifier", header_name="Box Identifier", editable=True)
    gb.configure_column("location", header_name="Location", editable=True)
    gb.configure_grid_options(rowSelection="single", suppressRowDeselection=False)
    grid_options = gb.build()

    box_grid_response = AgGrid(
        box_df,
        gridOptions=grid_options,
        update_on=["cellValueChanged", "selectionChanged"],
    )

    selected_box = None
    if box_grid_response.event_data:
        if box_grid_response.event_data["type"] == "selectionChanged":
            selected_box = box_grid_response.selected_data
        elif box_grid_response.event_data["type"] == "cellValueChanged":
            update_box(
                box_grid_response.event_data["data"]["id"],
                box_grid_response.event_data["data"]["box_identifier"],
                box_grid_response.event_data["data"]["location"],
            )

    if selected_box is not None:
        selected_box = selected_box.iloc[0]
        # print(f"Selected Box ID: {selected_box["id"]}")

    st.sidebar.subheader("Add / Edit Box")
    box_identifier = st.sidebar.text_input("Box Identifier")
    location = st.sidebar.text_input("Location")

    if st.sidebar.button("Add Box"):
        insert_box(box_identifier, location)
        st.rerun()

    if selected_box is not None:
        if st.sidebar.button("Update Box"):
            update_box(selected_box["id"], box_identifier, location)
            st.rerun()

        if st.sidebar.button("Delete Box"):
            delete_box(selected_box["id"])
            st.rerun()

        # Display and manage items for the selected box
        st.header(f"Items in {selected_box['box_identifier']}")
        item_df = fetch_items(selected_box["id"])

        # Custom cell renderer for images
        image_cell_renderer = JsCode(
            """
            class ThumbnailRenderer {
                init(params) {
                    this.eGui = document.createElement('img');

                    const image = 'data:image/jpeg;base64,' + params.value;
                    this.eGui.src = image;
                    this.eGui.style.width = '50px';
                    this.eGui.style.height = 'auto';
                    this.eGui.style.objectFit = 'contain';
                }

                getGui() {
                    return this.eGui;
                }

                refresh(params) {
                    return false;
                }
            }
            """
        )

        igb = GridOptionsBuilder.from_dataframe(item_df)
        igb.configure_pagination()
        igb.configure_columns(["id", "box_id"], hide=True)
        igb.configure_column("name", header_name="Name", editable=True)
        igb.configure_column("category", header_name="Category", editable=True)
        igb.configure_column("description", header_name="Description", editable=True)
        igb.configure_column("price", header_name="Price", editable=True)
        igb.configure_column(
            "image", header_name="Image", cellRenderer=image_cell_renderer
        )
        igb.configure_grid_options(rowSelection="single", suppressRowDeselection=False)
        item_grid_options = igb.build()

        item_grid_response = AgGrid(
            item_df,
            gridOptions=item_grid_options,
            allow_unsafe_jscode=True,
            update_on=["cellValueChanged", "selectionChanged"],
        )

        selected_item = None
        if item_grid_response.event_data:
            if item_grid_response.event_data["type"] == "selectionChanged":
                selected_item = item_grid_response.selected_data
            elif item_grid_response.event_data["type"] == "cellValueChanged":
                update_item(
                    item_grid_response.event_data["data"]["id"],
                    item_grid_response.event_data["data"]["name"],
                    item_grid_response.event_data["data"]["category"],
                    item_grid_response.event_data["data"]["description"],
                    item_grid_response.event_data["data"]["price"],
                    item_grid_response.event_data["data"]["image"],
                )
        st.sidebar.subheader("Add / Edit Item")
        item_name = st.sidebar.text_input("Item Name")
        category = st.sidebar.text_input("Category")
        description = st.sidebar.text_area("Description")
        price = st.sidebar.number_input("Price", min_value=0.0)
        image = st.sidebar.file_uploader("Image", type=["png", "jpg", "jpeg"])

        if image is not None:
            image_data = image.read()
            st.sidebar.image(image_data, caption=image.name, use_column_width=True)
        else:
            image_data = None

        if st.sidebar.button("Add Item"):
            insert_item(
                int(selected_box["id"]),
                item_name,
                category,
                description,
                price,
                image_data,
            )
            st.rerun()

        if selected_item is not None:
            selected_item = selected_item.iloc[0]
            # print(f"Selected Item ID: {selected_item["id"]}")
            if st.sidebar.button("Update Item"):
                update_item(
                    selected_item["id"],
                    item_name,
                    category,
                    description,
                    price,
                    image_data,
                )
                st.rerun()

            if st.sidebar.button("Delete Item"):
                delete_item(selected_item["id"])
                st.rerun()


if __name__ == "__main__":
    main()
