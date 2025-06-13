from website import create_app, db
from flask_migrate import Migrate

app = create_app()

if __name__ == '__main__':
    migrate = Migrate(app, db)
    app.run(debug=True)
   