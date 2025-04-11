import streamlit as st
import pandas as pd
import io
import base64

def allocate_seats(student_file_content, seats_la_lc_lh, seats_cc_kr, room_constraints):
    """Allocates seats based on student data and room constraints."""
    try:
        student_file = io.BytesIO(student_file_content.read())
        df_students = pd.read_excel(student_file)

        required_columns = ["Roll No", "Name"]
        if not all(col in df_students.columns for col in required_columns):
            st.error(f"⚠️ Error: The file must contain these columns: {required_columns}")
            return None

        df_seats_la_lc_lh = pd.read_excel(seats_la_lc_lh)
        df_seats_cc_kr = pd.read_excel(seats_cc_kr)

        # Normalize case in seat data
        df_seats_la_lc_lh["Color"] = df_seats_la_lc_lh["Color"].str.strip().str.lower()
        df_seats_cc_kr["Parity"] = df_seats_cc_kr["Parity"].str.strip().str.lower()

        allocated_seats = []
        remaining_students = df_students.copy()

        for room, constraints in room_constraints.items():
            if room.startswith(("LA", "LC", "LH")):
                for position, colors in constraints.items():
                    for color in colors:
                        color = color.strip().lower()  # normalize color
                        valid_seats = df_seats_la_lc_lh[
                            (df_seats_la_lc_lh["Room Number"] == room)
                            & (df_seats_la_lc_lh["Position"] == position)
                            & (df_seats_la_lc_lh["Color"] == color)
                        ]

                        if valid_seats.empty:
                            continue

                        num_seats = min(len(valid_seats), len(remaining_students))
                        assigned_students = remaining_students.iloc[:num_seats].copy()
                        assigned_students["Seat Number"] = valid_seats.iloc[:num_seats]["Seat Number"].values
                        assigned_students["Room"] = room
                        assigned_students["Signature"] = ""

                        allocated_seats.append(assigned_students)
                        remaining_students = remaining_students.iloc[num_seats:]

            elif room.startswith(("CC", "KR")):
                parity_list = [p.strip().lower() for p in constraints.get("Parity", [])]
                valid_seats = df_seats_cc_kr[
                    (df_seats_cc_kr["Room Number"] == room)
                    & (df_seats_cc_kr["Parity"].isin(parity_list))
                ]

                if valid_seats.empty:
                    st.warning(f"⚠️ No valid seats for {room} with parity {parity_list}. Skipping...")
                    continue

                num_seats = min(len(valid_seats), len(remaining_students))
                assigned_students = remaining_students.iloc[:num_seats].copy()
                assigned_students["Seat Number"] = valid_seats.iloc[:num_seats]["Seat Number"].values
                assigned_students["Room"] = room
                assigned_students["Signature"] = ""

                allocated_seats.append(assigned_students)
                remaining_students = remaining_students.iloc[num_seats:]

        df_final = pd.concat(allocated_seats, ignore_index=True)[
            ["Roll No", "Name", "Seat Number", "Room", "Signature"]
        ]
        df_final["Roll No"] = df_final["Roll No"].astype(str)  # Ensures roll no is string
        return df_final

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

def main():
    st.title("IITB Seat Mapping System")

    student_file = st.file_uploader("Upload Student Data (Excel file)", type=["xlsx"])
    seats_la_lc_lh = st.file_uploader("Upload LA/LC/LH Seat Data (LA_LC_LH_final.xlsx)", type=["xlsx"])
    seats_cc_kr = st.file_uploader("Upload CC/KR Seat Data (CC_KR_final.xlsx)", type=["xlsx"])

    if student_file and seats_la_lc_lh and seats_cc_kr:
        rooms = [
            "LA 001", "LA 002", "LA 201", "LA 202", "LC 001", "LC 002", "LC 101",
            "LC 102", "LC 201", "LC 202", "LH 101", "LH 102", "LH 201", "LH 202",
            "CC 101", "CC 105", "KR 125", "KR 225", "CC 103"
        ]

        num_rooms = st.number_input("🔹 How many rooms do you want to specify?", min_value=0, step=1, value=1)
        room_constraints = {}

        for i in range(num_rooms):
            st.subheader(f"Room {i + 1} Constraints")
            room = st.selectbox(f"Select Room Number:", rooms, key=f"room_{i}")

            if room.startswith(("LA", "LC", "LH")):
                left_colors = [c.strip() for c in st.text_input(f"Enter allowed colors for {room} (Left), comma-separated: ", key=f"left_{i}").split(",") if c.strip()]
                middle_colors = [c.strip() for c in st.text_input(f"Enter allowed colors for {room} (Middle), comma-separated: ", key=f"middle_{i}").split(",") if c.strip()]
                right_colors = [c.strip() for c in st.text_input(f"Enter allowed colors for {room} (Right), comma-separated: ", key=f"right_{i}").split(",") if c.strip()]

                room_constraints[room] = {
                    "Left": left_colors,
                    "Middle": middle_colors,
                    "Right": right_colors,
                }

            elif room.startswith(("CC", "KR")):
                parity = st.selectbox(f"Should {room} have 'Even' or 'Odd' seat numbers?", ["Even", "Odd"], key=f"parity_{i}")
                room_constraints[room] = {"Parity": [parity]}

        if st.button("Allocate Seats"):
            df_final = allocate_seats(student_file, seats_la_lc_lh, seats_cc_kr, room_constraints)

            if df_final is not None:
                st.dataframe(df_final)
                st.markdown(get_table_download_link(df_final), unsafe_allow_html=True)
                st.success("Seat allocation completed!")

def get_table_download_link(df):
    """Generates a download link for a dataframe as Excel."""
    towrite = io.BytesIO()
    df.to_excel(towrite, index=False, header=True)
    towrite = towrite.getvalue()
    b64 = base64.b64encode(towrite).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="allocated_seats.xlsx">Download Excel file</a>'
    return href

if __name__ == "__main__":
    main()
