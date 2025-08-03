import streamlit as st
import pandas as pd
import sqlite3
import random

# Connect to the SQLite database
conn = sqlite3.connect("pregnancy_q_table.db", check_same_thread=False)
cursor = conn.cursor()

# Load the dataset (Assuming it's already cleaned and preprocessed)
dataset = pd.read_csv("/content/drive/MyDrive/merged_pregnancy_food_dataset.csv")

# Helper: Get distinct users from the database
def get_existing_users():
    cursor.execute("SELECT DISTINCT user_id FROM q_table")
    return [row[0] for row in cursor.fetchall()]

# Helper: Load Q-values for a user
def load_q_table(user_id):
    cursor.execute("SELECT state, action, q_value FROM q_table WHERE user_id = ?", (user_id,))
    return {(row[0], row[1]): row[2] for row in cursor.fetchall()]

# Helper: Save Q-value
def save_q_value(user_id, state, action, q_value):
    cursor.execute("""
        INSERT INTO q_table (user_id, state, action, q_value)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, state, action) DO UPDATE SET q_value = ?
    """, (user_id, state, action, q_value, q_value))
    conn.commit()

# Helper: Calculate Reward
def calculate_reward(food, user_input):
    reward = 0
    if user_input['trimester'] == 1 and food['Folate (µg per 100g)'] > 100:
        reward += 15
    if user_input['trimester'] == 2 and food['Iron (mg per 100g)'] > 5:
        reward += 20
    if user_input['trimester'] == 3 and food['Omega-3 (g per 100g)'] > 0.1:
        reward += 25

    if user_input['health_condition'] == 'anemia' and food['Anemia Friendly'] == 'Yes':
        reward += 20
    if user_input['health_condition'] == 'gestational_diabetes' and food['Gestational Diabetes Friendly'] == 'Yes':
        reward += 15
    if user_input['health_condition'] == 'hypertension' and food['Sodium (mg per 100g)'] < 50:
        reward += 10

    if food['Sodium (mg per 100g)'] > 100:
        reward -= 20
    if user_input['health_condition'] == 'gestational_diabetes' and food['Energy (kcal per 100g)'] > 400:
        reward -= 15

    return reward

# Streamlit UI
st.title("🤰 Pregnancy Food Recommendation System")
st.markdown("---")

# User login or creation
user_mode = st.radio("Select User Mode", ["Existing User", "New User"])
if user_mode == "Existing User":
    users = get_existing_users()
    user_id = st.selectbox("Select your User ID", users)
else:
    user_id = st.text_input("Enter new User ID")

if user_id:
    # Collect inputs
    trimester = st.selectbox("Your Trimester", [1, 2, 3])
    condition = st.selectbox("Health Condition", ["anemia", "gestational_diabetes", "hypertension", "none"])
    preference = st.selectbox("Dietary Preference", ["Vegetarian", "Vegan", "Gluten-Free", "None"])

    user_input = {
        "trimester": trimester,
        "health_condition": condition,
        "dietary_preference": preference
    }

    state = f"{trimester}, {condition}"
    q_table = load_q_table(user_id)

    # Recommend top 3 foods with highest Q-values for the given state
    st.markdown("---")
    st.subheader("📌 Top Recommended Foods")

    ranked_foods = []
    for idx, row in dataset.iterrows():
        action = row['Food Name']
        q_value = q_table.get((state, action), 0)
        ranked_foods.append((q_value, idx, action))

    top_recommendations = sorted(ranked_foods, reverse=True)[:3]

    for q_value, idx, action in top_recommendations:
        food = dataset.iloc[idx]
        reward = calculate_reward(food, user_input)

        st.markdown(f"**🍲 Food:** {action}")
        st.markdown(f"- Health Benefit: {'Anemia Friendly' if food['Anemia Friendly'] == 'Yes' else 'Not Anemia Friendly'}")
        st.markdown(f"- Q-Value (Before Feedback): {round(q_value, 2)}")

        feedback = st.radio(f"Do you like this recommendation for {action}?", ["yes", "no"], key=action)

        if feedback == "yes":
            reward += 10
        else:
            reward -= 10

        # Update Q-value
        new_q = q_value + 0.1 * (reward - q_value)
        save_q_value(user_id, state, action, new_q)

        st.markdown(f"✅ **Updated Q-Value:** {round(new_q, 2)}")
        st.markdown("---")
