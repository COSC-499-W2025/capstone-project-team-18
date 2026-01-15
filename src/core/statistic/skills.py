"""
This file provides functionality to map imports, filenames and keywords to skills
such as DevOps or Machine Learning
"""

from typing import Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Skill(Enum):
    MACHINE_LEARNING = "Machine Learning"
    DATA_ANALYTICS = "Data Analytics"
    DEVOPS = "DevOps"
    CI_CD = "CI/CD"
    WEB_DEVELOPMENT = "Web Development"
    CLOUD_COMPUTING = "Cloud Computing"
    DATABASE = "Database"
    TESTING = "Testing"
    CONTAINERIZATION = "Containerization"
    API_DEVELOPMENT = "API Development"
    MOBILE_DEVELOPMENT = "Mobile Development"
    SECURITY = "Security"


@dataclass
class SkillIndicator:
    """Represents an indicator that suggests a particular skill"""
    packages: Set[str]  # Package names or patterns
    file_patterns: Set[str]  # File name patterns  -> Dockerfile /
    file_extensions: Set[str]
    # Keywords in file contents (not currently integrated ue to processing concerns)
    keywords: Set[str]


class SkillMapper:
    """
    Maps imported packages, file patterns, and file names to high-level skills.
    """

    # Define skill indicators for each high-level skill -> Examples given by GenAI
    SKILL_INDICATORS: Dict[Skill, SkillIndicator] = {
        Skill.MACHINE_LEARNING: SkillIndicator(
            packages={
                # Python ML frameworks
                'tensorflow', 'tf', 'keras', 'torch', 'pytorch', 'sklearn',
                'scikit-learn', 'xgboost', 'lightgbm', 'catboost',
                'transformers', 'huggingface', 'fastai', 'mxnet',
                'jax', 'flax', 'stable-baselines3', 'ray',
                # Python ML utilities
                'mlflow', 'wandb', 'tensorboard', 'optuna',
                'hyperopt', 'sacred', 'comet_ml',
                # Model formats
                'onnx', 'tensorrt', 'tflite',
                # JavaScript/TypeScript ML
                'tensorflow.js', '@tensorflow/tfjs', 'brain.js', 'ml5',
                'synaptic', 'convnetjs',
                # Java ML
                'weka', 'deeplearning4j', 'dl4j', 'mallet',
                # R packages
                'caret', 'mlr', 'mlr3', 'randomforest',
                # C++ ML
                'dlib', 'mlpack', 'shark'
            },
            file_patterns={
                # Model files (language agnostic)
                'model.pkl', 'model.h5', 'model.pt', 'model.pth',
                '*.onnx', '*.tflite', '*.pb', '*.pmml',
                # Training/inference files
                'train.*', 'training.*', 'inference.*', 'predict.*',
                'model.*', 'model_*', '*_model.*',
                # Config files
                'requirements.txt', 'environment.yml', 'conda.yml',
                # Notebooks
                '*.ipynb', '*.rmd'
            },
            file_extensions={'.ipynb', '.pkl', '.h5', '.pt',
                             '.pth', '.pb', '.onnx', '.tflite', '.pmml', '.rmd'},
            keywords={
                'neural_network', 'deep_learning', 'training', 'inference',
                'model', 'dataset', 'epoch', 'batch_size', 'learning_rate',
                'classifier', 'regression', 'prediction', 'accuracy'
            }
        ),

        Skill.DATA_ANALYTICS: SkillIndicator(
            packages={
                # Python data manipulation
                'pandas', 'numpy', 'polars', 'dask', 'modin',
                # Python visualization
                'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair',
                'dash', 'streamlit', 'gradio',
                # Python statistics
                'scipy', 'statsmodels', 'pingouin',
                # Data processing
                'pyspark', 'spark', 'arrow', 'pyarrow', 'duckdb',
                # Jupyter
                'jupyter', 'ipython', 'notebook',
                # JavaScript/TypeScript
                'd3', 'd3.js', 'chart.js', 'chartjs', 'highcharts',
                'plotly.js', 'echarts', 'vega', 'vega-lite',
                # R packages
                'ggplot2', 'dplyr', 'tidyr', 'shiny', 'tidyverse',
                # Java
                'jfreechart', 'tablesaw'
            },
            file_patterns={
                # Notebooks
                '*.ipynb', '*.rmd',
                # Analysis files (any language)
                'analysis.*', 'analyze.*', '*_analysis.*',
                'viz.*', 'visualize.*', 'visualization.*', '*_viz.*',
                'dashboard.*', '*_dashboard.*',
                'report.*', '*_report.*',
                'eda.*', '*_eda.*', 'exploratory.*',
                # Data files
                '*.csv', '*.parquet', '*.feather', '*.arrow',
                # BI files
                '*.pbix', '*.twb', '*.twbx'
            },
            file_extensions={
                '.ipynb', '.rmd', '.csv', '.parquet', '.feather', '.arrow',
                '.pbix', '.twb', '.twbx', '.xlsx', '.xlsm'
            },
            keywords={
                'dataframe', 'visualization', 'analysis', 'dashboard',
                'exploratory', 'statistical', 'correlation', 'distribution',
                'analytics', 'metrics', 'insights', 'reporting'
            }
        ),

        Skill.DEVOPS: SkillIndicator(
            packages={
                # Python
                'ansible', 'salt', 'puppet', 'chef',
                'prometheus', 'grafana', 'datadog', 'newrelic',
                'sentry', 'elasticsearch', 'logstash', 'kibana',
                'fabric', 'invoke', 'paramiko',
                # Ruby
                'capistrano', 'rake',
                # JavaScript/Node
                'pm2', 'forever', 'nodemon'
            },
            file_patterns={
                # Deployment scripts (any language)
                'deploy*', 'deployment*', 'setup*', 'install*',
                # Ansible
                'playbook*', 'ansible*', '*.ansible',
                # Monitoring/alerting
                'monitor*', 'alert*', 'logging*',
                # Build scripts
                'build*', 'make*', 'rake*',
                # Config files
                'Vagrantfile', 'Berksfile'
            },
            file_extensions={'.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd'},
            keywords={
                'deployment', 'monitoring', 'logging', 'orchestration',
                'automation', 'provisioning', 'configuration', 'infrastructure'
            }
        ),

        Skill.CI_CD: SkillIndicator(
            packages={
                # Testing frameworks (multiple languages)
                'pytest', 'unittest', 'nose', 'tox',  # Python
                'jest', 'mocha', 'jasmine', 'karma', 'cypress',  # JavaScript
                'junit', 'testng', 'mockito',  # Java
                'rspec', 'minitest',  # Ruby
                'phpunit',  # PHP
                # CI/CD tools
                'jenkins', 'travis', 'gitlab', 'github', 'circleci', 'actions'
            },
            file_patterns={
                # GitHub Actions
                '.github/workflows/*', '*.github-workflow.yml',
                # GitLab CI
                '.gitlab-ci.yml', '.gitlab-ci.yaml',
                # Jenkins
                'Jenkinsfile', 'Jenkinsfile.*',
                # Travis CI
                '.travis.yml',
                # CircleCI
                '.circleci/*', 'circle.yml',
                # Azure Pipelines
                'azure-pipelines.yml', 'azure-pipelines.yaml',
                # Bitbucket
                'bitbucket-pipelines.yml',
                # Generic pipeline/build files
                'pipeline*', 'build*', 'test*',
                # Makefile
                'Makefile', 'makefile', '*.mk',
                # Other build tools
                'Rakefile', 'Gruntfile*', 'Gulpfile*', 'webpack.config.*',
                'rollup.config.*', 'vite.config.*'
            },
            file_extensions={'.yml', '.yaml', '.mk'},
            keywords={
                'pipeline', 'workflow', 'build', 'deploy', 'test',
                'continuous_integration', 'continuous_deployment', 'ci', 'cd',
                'automation', 'release'
            }
        ),

        Skill.CONTAINERIZATION: SkillIndicator(
            packages={
                'docker', 'podman', 'kubernetes', 'k8s',
                'docker-compose', 'helm'
            },
            file_patterns={
                'Dockerfile', 'Dockerfile.*', 'docker-compose*.yml',
                'docker-compose*.yaml', '.dockerignore',
                'deployment*.yaml', 'deployment*.yml',
                'service*.yaml', 'service*.yml',
                'pod*.yaml', 'pod*.yml'
            },
            file_extensions={},
            keywords={
                'container', 'image', 'orchestration', 'pod',
                'deployment', 'service', 'ingress', 'namespace'
            }
        ),

        Skill.CLOUD_COMPUTING: SkillIndicator(
            packages={
                # Python
                'boto3', 'botocore', 'awscli', 'aws',
                'azure', 'azure-storage', 'azure-functions',
                'google-cloud', 'gcloud', 'gcp',
                's3fs', 'adlfs', 'gcsfs',
                # JavaScript/Node
                'aws-sdk', '@aws-sdk', 'azure-storage', '@azure',
                '@google-cloud', 'firebase', 'firebase-admin',
                # Java
                'aws-java-sdk', 'azure-sdk', 'google-cloud-java',
                # .NET
                'awssdk', 'azure.storage', 'google.cloud'
            },
            file_patterns={
                # AWS Lambda
                'lambda_*', 'lambda.*', '*_lambda.*', 'handler.*',
                # Azure Functions
                'function_*', 'function.*', '*_function.*', 'function.json',
                # Google Cloud Functions
                'cloud_*', 'gcf_*',
                # Generic cloud files
                'aws_*', 'azure_*', 'gcp_*', 'cloud*',
                # Serverless
                'serverless.yml', 'serverless.yaml', 'serverless.json'
            },
            file_extensions={'.tf', '.tfvars'},
            keywords={
                'lambda', 'function', 'serverless', 'bucket',
                's3', 'blob', 'storage', 'compute', 'instance',
                'cloud', 'aws', 'azure', 'gcp', 'firebase'
            }
        ),

        Skill.DATABASE: SkillIndicator(
            packages={
                # Python - Relational
                'psycopg2', 'pymysql', 'sqlite3', 'sqlalchemy',
                'django', 'flask-sqlalchemy', 'peewee', 'pony', 'tortoise',
                # Python - NoSQL
                'pymongo', 'redis', 'cassandra', 'neo4j', 'elasticsearch',
                # JavaScript/Node
                'mongoose', 'sequelize', 'typeorm', 'prisma', 'knex',
                'pg', 'mysql', 'mysql2', 'mongodb', 'redis',
                # Java
                'hibernate', 'jdbc', 'jpa', 'mybatis',
                # .NET
                'entityframework', 'dapper',
                # Ruby
                'activerecord', 'sequel', 'mongoid',
                # PHP
                'doctrine', 'eloquent', 'pdo'
            },
            file_patterns={
                # SQL files
                '*.sql', 'schema*', 'migration*', 'seed*',
                # Migration files (various frameworks)
                '*_migration.*', 'migrations/*',
                # Model/ORM files
                'model*', 'models/*', '*_model.*',
                # Database config
                'db*', 'database*', '*_db.*',
                # Liquibase/Flyway
                'changelog*', 'flyway*', 'liquibase*'
            },
            file_extensions={'.sql', '.ddl', '.dml'},
            keywords={
                'database', 'query', 'migration', 'schema',
                'table', 'index', 'transaction', 'orm', 'sql',
                'select', 'insert', 'update', 'delete', 'join'
            }
        ),

        Skill.TESTING: SkillIndicator(
            packages={
                # Python
                'pytest', 'unittest', 'nose', 'mock', 'faker',
                'hypothesis', 'coverage', 'tox',
                # JavaScript
                'jest', 'mocha', 'chai', 'jasmine', 'karma',
                'enzyme', '@testing-library', 'vitest',
                # Browser testing
                'selenium', 'playwright', 'puppeteer', 'cypress',
                'webdriver', 'webdriverio',
                # Java
                'junit', 'testng', 'mockito', 'assertj',
                # Ruby
                'rspec', 'minitest', 'capybara',
                # PHP
                'phpunit', 'codeception',
                # .NET
                'nunit', 'xunit', 'mstest',
                # Go
                'testify', 'gomock'
            },
            file_patterns={
                # Test files (various naming conventions)
                'test_*', '*_test.*', '*.test.*', '*.spec.*',
                'tests/*', 'test/*', '__tests__/*', 'spec/*',
                # Configuration
                'conftest.*', 'pytest.ini', 'tox.ini',
                'jest.config.*', 'karma.conf.*', 'mocha.opts',
                'phpunit.xml', 'phpunit.xml.dist'
            },
            file_extensions={},
            keywords={
                'test', 'fixture', 'mock', 'assertion', 'assert',
                'coverage', 'integration', 'unit', 'e2e', 'acceptance',
                'expect', 'should', 'describe', 'it'
            }
        ),

        Skill.WEB_DEVELOPMENT: SkillIndicator(
            packages={
                # Python
                'django', 'flask', 'fastapi', 'tornado', 'bottle',
                'pyramid', 'aiohttp', 'sanic', 'quart', 'starlette',
                # JavaScript/Node
                'express', 'koa', 'hapi', 'nestjs',
                # Frontend frameworks
                'react', 'vue', 'angular', 'svelte', 'solid',
                'next', 'nuxt', 'gatsby', 'remix', 'astro',
                # Ruby
                'rails', 'sinatra', 'hanami',
                # PHP
                'laravel', 'symfony', 'codeigniter', 'cakephp',
                # Java
                'spring', 'springboot', 'struts', 'jsf',
                # .NET
                'aspnet', 'asp.net', 'mvc',
                # Go
                'gin', 'echo', 'fiber', 'chi'
            },
            file_patterns={
                # Backend
                'server.*', 'api.*', 'routes.*', 'router.*',
                'views.*', 'controller*', 'middleware*',
                # Frontend
                'index.html', 'index.jsx', 'index.tsx',
                'App.jsx', 'App.tsx', 'App.vue',
                # Templates
                'templates/*', 'views/*',
                # Static files
                'static/*', 'public/*', 'assets/*',
                # Config
                'package.json', 'webpack.config.*', 'vite.config.*'
            },
            file_extensions={
                '.html', '.htm', '.css', '.scss', '.sass', '.less',
                '.jsx', '.tsx', '.vue', '.svelte'
            },
            keywords={
                'api', 'endpoint', 'route', 'view', 'template',
                'middleware', 'request', 'response', 'http', 'server',
                'web', 'frontend', 'backend', 'component'
            }
        ),

        Skill.API_DEVELOPMENT: SkillIndicator(
            packages={
                # Python
                'fastapi', 'flask', 'django', 'rest_framework',
                'graphql', 'graphene', 'ariadne', 'strawberry',
                'apispec', 'swagger', 'openapi', 'pydantic', 'marshmallow',
                # JavaScript/Node
                'express', 'apollo', 'graphql', '@apollo/server',
                'swagger-ui-express', 'swagger-jsdoc', 'joi',
                # Java
                'spring-web', 'jersey', 'resteasy', 'swagger',
                # .NET
                'webapi', 'aspnetcore',
                # Go
                'gin', 'echo', 'gorilla/mux'
            },
            file_patterns={
                # API files
                'api.*', 'api_*', '*_api.*', 'apis/*',
                # Routes/endpoints
                'route*', 'router*', 'endpoint*',
                # Schemas
                'schema*', 'schemas/*', '*_schema.*',
                # API documentation
                'swagger.*', 'openapi.*', '*.swagger.*', '*.openapi.*',
                'api-spec.*', 'api.yml', 'api.yaml', 'api.json',
                # GraphQL
                '*.graphql', '*.gql', 'schema.gql'
            },
            file_extensions={'.graphql', '.gql'},
            keywords={
                'api', 'endpoint', 'rest', 'restful', 'graphql',
                'request', 'response', 'authentication', 'authorization',
                'swagger', 'openapi', 'schema', 'validation'
            }
        ),

        Skill.MOBILE_DEVELOPMENT: SkillIndicator(
            packages={
                # Cross-platform
                'react-native', 'expo', 'flutter', 'ionic', 'cordova',
                'capacitor', 'nativescript',
                # Python mobile
                'kivy', 'beeware', 'toga',
                # Native iOS (via packages that might appear)
                'cocoapods', 'alamofire', 'rxswift',
                # Native Android
                'retrofit', 'room', 'navigation', 'lifecycle'
            },
            file_patterns={
                # React Native
                'App.js', 'App.jsx', 'App.tsx',
                # Flutter
                'main.dart', 'pubspec.yaml',
                # iOS
                'Podfile', 'Podfile.lock', 'Info.plist',
                'AppDelegate.*', '*.xcodeproj', '*.xcworkspace',
                # Android
                'AndroidManifest.xml', 'build.gradle', 'settings.gradle',
                'MainActivity.*', 'app/src/*',
                # Capacitor/Ionic
                'capacitor.config.*', 'ionic.config.*'
            },
            file_extensions={
                '.dart', '.swift', '.kt', '.kts',
                '.m', '.mm', '.storyboard', '.xib'
            },
            keywords={
                'mobile', 'android', 'ios', 'native',
                'app', 'navigation', 'screen', 'activity',
                'viewcontroller', 'widget', 'platform'
            }
        ),

        Skill.SECURITY: SkillIndicator(
            packages={
                'cryptography', 'pycryptodome', 'hashlib',
                'jwt', 'pyjwt', 'oauth', 'authlib',
                'passlib', 'bcrypt', 'secrets'
            },
            file_patterns={
                'auth*', 'security*', 'crypto*',
                'authentication*', 'authorization*'
            },
            file_extensions={},
            keywords={
                'authentication', 'authorization', 'encryption',
                'hash', 'token', 'password', 'security', 'crypto'
            }
        )
    }

    @classmethod
    def map_package_to_skill(cls, package: str) -> Optional[Skill]:
        """
        Maps a single package name to a high-level skill.

        Args:
            package: Package name (e.g., 'pandas', 'tensorflow')

        Returns:
            Skill enum if matched, None otherwise
        """
        normalized_package = package.split('.')[0].lower()

        for skill, indicators in cls.SKILL_INDICATORS.items():
            if normalized_package in indicators.packages:
                return skill

        return None

    @classmethod
    def map_filepath_to_skill(cls, filepath: str) -> Optional[Skill]:
        """
        Maps a file path to a high-level skill based on patterns and extensions.

        Args:
            filepath: Path to the file (relative to the root directory of its associated project)
        Returns:
            Skill enum if matched, None otherwise
        """
        path = Path(filepath)
        extension = path.suffix.lower()

        for skill, indicators in cls.SKILL_INDICATORS.items():
            # Check file extensions
            if extension and extension in indicators.file_extensions:
                return skill

            # Check file patterns
            if cls._matches_any_pattern(filepath, indicators.file_patterns):
                return skill

        return None

    @staticmethod
    def _matches_any_pattern(filepath: str, patterns: Set[str]) -> bool:
        """Check if filepath matches any pattern in the set"""
        path = Path(filepath)
        filename = path.name.lower()
        filepath_lower = str(path).lower()

        for pattern in patterns:
            # Handle directory patterns (e.g., '.github/workflows/*')
            if '/' in pattern:
                if pattern.lower().replace('*', '').strip('/') in filepath_lower:
                    return True

            # Handle wildcard patterns (e.g., '*.tf')
            elif pattern.startswith('*'):
                if filename.endswith(pattern[1:].lower()):
                    return True

            elif pattern.endswith('*'):
                if filename.startswith(pattern[:-1].lower()):
                    return True

            # Exact match
            elif filename == pattern.lower():
                return True

        return False
