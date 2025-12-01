# TODO: get profile value from client 
from enum import Enum


profile = """
À propos d’Yingqi
Passionnée par le développement logiciel et spécialisée en full-stack, je conçois et développe des applications robustes, scalables et maintenables.
Mon objectif : livrer du code propre, optimisé et aligné avec les besoins métier 🎯.

🔧 Compétences techniques

— Développement full-stack : conception, développement, tests, maintenance
— Backend : Python 🐍 • Java ☕ • C++ ⚙️
— Frontend : Angular 🅰️ • React ⚛️ • Flutter
— Développement mobile : Flutter 📱 • React Native 📲
— Architecture logicielle : systèmes robustes, modulaires et scalables
— API REST : intégration backend, communication entre services 🔌
— Déploiement serveur et optimisation des performances 🚀
— Bonnes pratiques : tests 🧪 • documentation 📘 • qualité de code 🧼 • gestion de versions (Git) 🔄

🧭 Méthode de travail

→ Approche agile, itérative et collaborative
→ Analyse claire des besoins avant développement
→ Propositions techniques réalistes et adaptées
→ Code propre, maintenable et documenté
→ Communication simple et fréquente tout au long du projet
→ Livraison dans les délais avec tests et validation finale ✔️

💡 Ce qui me motive

— Résoudre des problèmes complexes
— Concevoir des architectures solides
— Construire des applications fiables, modernes et évolutives
— Mettre mon expertise technique au service de projets ambitieux 🚀

🤝 Collaboration

Je serai ravie de découvrir votre projet et d’y contribuer avec efficacité, créativité et sens du détail.
"""

project_list = []


class ProjectStatus(str, Enum):
    NEW = "new"
    ANSWERED = "answered"
    REJECTED = "rejected"
    PENDING = "pending"


PROJECT_STATUS_VALUES = {status.value for status in ProjectStatus}