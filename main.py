# # main.py

# import os
# from website import create_app

# app = create_app()

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 8080))  # Use PORT=8080 from Cloud Run
#     app.run(host='0.0.0.0', port=port)


# # app = create_app()

# # if __name__ == '__main__':
# #     app.run(debug=True, host='0.0.0.0', port=5000)

import os
from website import create_app

try:
    app = create_app()
except Exception as e:
    print("App failed to start:", e)
    raise e  # Ensure Cloud Run logs the actual error

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
