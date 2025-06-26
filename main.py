# main.py

import os
from website import create_app

app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))  # Use PORT=8080 from Cloud Run
    app.run(host='0.0.0.0', port=port)
from website import create_app, db


# app = create_app()

# if __name__ == '__main__':
#     app.run(debug=True)
     