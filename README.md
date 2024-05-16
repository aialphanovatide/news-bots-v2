### Managing Database Migrations in Flask with Flask-Migrate

In Flask development, handling the database structure securely and efficiently is crucial. Flask-Migrate, integrated with Alembic, facilitates this process through specific commands that allow versioning and modification of the database schema. Below are the key commands for working with Flask-Migrate.

#### Initialization of Migrations

Before you can work with migrations, you need to set up Flask-Migrate in your project. This is typically done once:

```bash
flask db init
```

This command creates a folder named `migrations` in your project, which will store all files related to migrations.

#### Creating Migrations

When you make changes to your models (e.g., adding a new column or a new table), you need to generate a migration to represent those changes:

```bash
flask db migrate -m "Description of the migration"
```

The `-m` flag allows you to provide a message describing the changes made, similar to a commit message in version control systems like git. This command does not change the database; it only generates the necessary migration files in the `migrations` folder.

#### Applying Migrations

To apply the generated migrations to your database, you use:

```bash
flask db upgrade
```

This command updates the database to reflect the changes defined in the migrations. Essentially, it executes the migration code that alters the database schema.

#### Reverting Migrations

If you need to undo a migration, you can use the command:

```bash
flask db downgrade
```

This command allows you to revert to the previous version of the database schema, as defined in the migration scripts.

### Summary

These commands form the foundation for managing your database schema in a Flask application:

- **`flask db init`** prepares your project to handle migrations.
- **`flask db migrate -m "Description"`** generates migration files for changes to the database schema.
- **`flask db upgrade`** applies migrations to update the database schema.
- **`flask db downgrade`** reverts migrations to previous versions of the database schema.
