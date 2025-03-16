# College Chatbot

This project is a chatbot designed to assist users with information related to a college website. It uses various libraries and APIs to fetch, process, and respond to user queries.

## Project Structure

```
.env
.gitignore
app.py
college_bot.py
requirements.txt
```

- `.env`: Contains environment variables such as the API key.
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `app.py`: The main application file that runs the Streamlit app.
- `college_bot.py`: Contains the `College` class which handles data fetching, processing, and generating responses.
- `requirements.txt`: Lists the dependencies required for the project.

## Setup

1. **Clone the repository:**

    ```sh
    git clone <repository-url>
    cd college_chatbot
    ```

2. **Create a virtual environment:**

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install the dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Set up the environment variables:**

    Create a `.env` file in the root directory and add your API key:

    ```env
    API_KEY="your_api_key_here"
    ```

## Running the Application

To run the Streamlit app, use the following command:

```sh
streamlit run app.py
```

This will start the Streamlit server, and you can interact with the chatbot through the web interface.

## Usage

- The chatbot can answer questions related to the college website by fetching and processing data from specified URLs.
- The chatbot can also respond to greetings appropriately.

## Logging

Logs are stored in the `college_bot.log` file, which includes information about the initialization, data fetching, processing, and any errors encountered.

## Dependencies

The project relies on the following libraries:

- `langchain-community`
- `html2text`
- `langchain_mistralai`
- `streamlit`
- `langchain_core`
- `python-dotenv`
- `requests`
- `beautifulsoup4`

These dependencies are listed in the `requirements.txt` file and can be installed using `pip`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.