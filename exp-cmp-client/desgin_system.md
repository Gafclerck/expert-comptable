# LedgerX - Design System & Documentation

Ce document est une reconstruction fidèle et détaillée du Design System de l'interface "LedgerX". Il est structuré pour être directement exploitable comme documentation de référence pour Figma et le développement.

> **Légende :** `[Exact]` (Identifié avec confiance), `[Estimated]` (Déduit visuellement), `[Recommended]` (Valeur proposée pour compléter le système).

---

## 1. Analyse visuelle générale

*   **Style visuel général :** Fintech premium, Dark Mode immersif, inspiré des interfaces Apple (macOS/iOS) avec une touche de modernité "glassmorphism".
*   **Direction artistique :** Interface élégante, lisse et sophistiquée. Elle utilise des dégradés de couleurs vifs (violet, cyan, vert) sur des fonds sombres pour créer un effet de "néon" ou de "glow", mettant en valeur les données financières.
*   **Niveau de minimalisme :** Modéré. L'interface est épurée, mais riche en informations chiffrées et graphiques. L'utilisation de la transparence évite la surcharge visuelle.
*   **Densité de l'interface :** Moyenne à élevée (typique d'un dashboard financier), mais organisée en blocs aérés pour rester lisible.
*   **Hiérarchie visuelle :** Très forte. Les chiffres clés sont grands et lumineux, les titres sont clairs, et les actions secondaires sont atténuées.
*   **Principes d'espacement :** Généreux. Les éléments respirent (padding interne des cartes important, gaps entre les cartes notables).
*   **Formes et géométrie :** Utilisation massive de formes très arrondies (coins de cartes, boutons en pilule, graphiques circulaires).
*   **Style des bordures :** Très fines, souvent quasi invisibles sur le fond sombre, ou utilisant une opacité très faible (blanc 5-10%) pour délimiter les surfaces sans alourdir.
*   **Style des ombres :** Double nature : ombres portées sombres douces, mais surtout un **Glow coloré** (halo) derrière les cartes ou les éléments de données pour une sensation de profondeur et de modernité.
*   **Utilisation du glassmorphism :** Oui, sur les cartes (fond sombre semi-transparent avec léger flou) pour laisser transparaître subtilement le fond.
*   **Rapport entre éléments pleins, transparents et semi-transparents :**
    *   **Pleins :** Boutons primaires violets, certains badges (Scheduled).
    *   **Semi-transparents :** La plupart des cartes, sur un fond légèrement plus clair.
    *   **Transparents :** Les fonds globaux et les zones de navigation.
*   **Principes de contraste :** Fort contraste entre le texte blanc (pur ou légèrement grisé) et les fonds sombres. Le texte secondaire est gris moyen pour rester lisible sans attirer l'attention.
*   **Sensation générale :** Moderne, fiable, high-tech et très lisible pour des données complexes.

---

## 2. Color Design Tokens

Les couleurs sont dérivées de l'image, en mettant l'accent sur la teinte "bleu nuit" et les accents violets/cyan.

### Couleurs de fond et de surface

| Nom du Token | HEX Estimé | RGB | HSL | Usage | Priorité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `color.background.primary` | `#09090B` | `rgb(9, 9, 11)` | `hsl(240, 10%, 4%)` | Fond global de l'application | `[Estimated]` |
| `color.surface.primary` | `#131316` | `rgb(19, 19, 22)` | `hsl(240, 7%, 8%)` | Fond des cartes "solides" | `[Estimated]` |
| `color.surface.glass` | `rgba(28, 28, 34, 0.7)` | `rgb(28, 28, 34)` | `hsl(240, 10%, 12%)` | Cartes Glassmorphism | `[Estimated]` |
| `color.surface.elevated` | `#1C1C22` | `rgb(28, 28, 34)` | `hsl(240, 10%, 12%)` | Éléments en surbrillance (Inputs) | `[Estimated]` |

### Couleurs de marque / Actions

| Nom du Token | HEX Estimé | RGB | HSL | Usage | Priorité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `color.primary` | `#8B5CF6` | `rgb(139, 92, 246)` | `hsl(258, 90%, 66%)` | Boutons principaux, logo, accents | `[Estimated]` |
| `color.primary.hover` | `#9D74F8` | `rgb(157, 116, 248)` | `hsl(258, 90%, 71%)` | État hover du bouton principal | `[Recommended]` |
| `color.primary.glow` | `rgba(139, 92, 246, 0.35)` | `rgb(139, 92, 246)` | `hsl(258, 90%, 66%)` | Halo lumineux violet | `[Estimated]` |
| `color.secondary` | `#3B82F6` | `rgb(59, 130, 246)` | `hsl(217, 91%, 60%)` | Boutons/liens secondaires, dégradés | `[Estimated]` |

### Couleurs sémantiques

| Nom du Token | HEX Estimé | RGB | HSL | Usage | Priorité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `color.success` | `#10B981` | `rgb(16, 185, 129)` | `hsl(160, 84%, 39%)` | Flèches de tendances positives, graphique | `[Estimated]` |
| `color.success.glow` | `rgba(16, 185, 129, 0.3)` | `rgb(16, 185, 129)` | `hsl(160, 84%, 39%)` | Halo vert derrière le graphique | `[Estimated]` |
| `color.warning` | `#F59E0B` | `rgb(245, 158, 11)` | `hsl(38, 92%, 50%)` | Flèches de tendances négatives | `[Estimated]` |
| `color.error` | `#EF4444` | `rgb(239, 68, 68)` | `hsl(0, 84%, 60%)` | Éléments de danger | `[Recommended]` |
| `color.info` | `#06B6D4` | `rgb(6, 182, 212)` | `hsl(189, 94%, 43%)` | Informations neutres | `[Recommended]` |

### Couleurs de texte

| Nom du Token | HEX Estimé | RGB | HSL | Usage | Priorité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `color.text.primary` | `#FFFFFF` | `rgb(255, 255, 255)` | `hsl(0, 0%, 100%)` | Titres, chiffres principaux | `[Exact]` |
| `color.text.secondary` | `#A1A1AA` | `rgb(161, 161, 170)` | `hsl(240, 5%, 65%)` | Texte descriptif, labels | `[Estimated]` |
| `color.text.muted` | `#71717A` | `rgb(113, 113, 122)` | `hsl(240, 4%, 46%)` | Placeholders, texte très secondaire | `[Estimated]` |
| `color.border` | `rgba(255, 255, 255, 0.08)` | `rgb(255, 255, 255)` | `hsl(0, 0%, 100%)` | Bordures des cartes | `[Estimated]` |
| `color.divider` | `rgba(255, 255, 255, 0.05)` | `rgb(255, 255, 255)` | `hsl(0, 0%, 100%)` | Séparateurs | `[Estimated]` |

---

## 3. Typography

**Police estimée :** **Inter** (ou alternative très proche comme Roboto ou SF Pro Display). C'est une police sans-serif contemporaine, très lisible sur écran, correspondant parfaitement aux interfaces fintech modernes.

### Échelle typographique complète

| Niveau | Font Weight | Font Size | Line Height | Letter Spacing | Text Transform | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Display** | Bold (700) | `40px` | `48px` | `-1%` | None | Grands chiffres (ex: `$456,789.33`) |
| **H1** | SemiBold (600) | `32px` | `40px` | `-0.5%` | None | Titre principal ("Sales Overview") |
| **H2** | SemiBold (600) | `24px` | `32px` | `0` | None | Titre de section ("My Cards") |
| **H3** | Medium (500) | `20px` | `28px` | `0` | None | Titre de sous-section |
| **H4** | Medium (500) | `16px` | `24px` | `0` | None | Titre de carte |
| **Body Large** | Regular (400) | `18px` | `28px` | `0` | None | Description principale |
| **Body** | Regular (400) | `16px` | `24px` | `0` | None | Texte standard, montants |
| **Body Small** | Regular (400) | `14px` | `20px` | `0` | None | Labels secondaires |
| **Caption** | Medium (500) | `12px` | `16px` | `0` | None | Métadonnées, dates |
| **Label** | Medium (500) | `14px` | `20px` | `0` | None | Libellés de navigation |
| **Button** | Medium (500) | `14px` | `20px` | `0` | None | Textes des boutons |
| **Input Text** | Regular (400) | `16px` | `24px` | `0` | None | Texte saisi dans les champs |

---

## 4. Spacing System

Le système d'espacement est basé sur une échelle de 4px, avec des gaps généreux.

| Token | Valeur (px) | Usage |
| :--- | :--- | :--- |
| `spacing.xs` | `4px` | Espacement entre les icônes et le texte dans les boutons |
| `spacing.sm` | `8px` | Gap entre éléments liés, marges intérieures des badges |
| `spacing.md` | `16px` | Padding standard des cartes, gap entre les éléments d'une liste |
| `spacing.lg` | `24px` | Padding des grandes cartes, gap entre les sections |
| `spacing.xl` | `32px` | Gap entre les cartes principales |
| `spacing.2xl` | `48px` | Marges entre les grandes sections |

**Détails :**
*   **Padding des cartes :** `16px` (card interne) et `24px` (card principale).
*   **Gap entre éléments (grid) :** `24px` (horizontal et vertical).
*   **Espacement entre titres et contenus :** `12px` à `16px`.
*   **Espacement des boutons :** `8px` entre les icônes et le texte.

---

## 5. Border Radius

L'interface privilégie les formes très rondes (style Apple). Les tokens suivants sont déduits :

| Token | Valeur (px) | Composants associés |
| :--- | :--- | :--- |
| `radius.xs` | `4px` | Badges très petits, indicateurs |
| `radius.sm` | `8px` | Petits composants, inputs |
| `radius.md` | `12px` | Boutons standard |
| `radius.lg` | `16px` | Cartes internes |
| `radius.xl` | `24px` | Cartes principales, modals |
| `radius.2xl` | `32px` | Conteneurs larges |
| `radius.full` | `9999px` | Boutons pilules, avatars, graphiques |

---

## 6. Borders

*   **Border Width :** `1px` (à l'exception des bordures des graphiques circulaires qui sont plus épaisses, ~12px).
*   **Border Color :** `rgba(255, 255, 255, 0.08)` (très subtil).
*   **Border Opacity :** 8% (pour les cartes), 5% (pour les diviseurs).
*   **Style :** `Solid`.
*   **Usage :**
    *   **Cards :** Bordure extrêmement subtile pour délimiter les blocs sans alourdir.
    *   **Inputs :** Bordure plus marquée à l'état focus (souvent de couleur primaire violette).
    *   **Buttons :** Boutons secondaires avec bordure subtile (1px) et fond transparent.

---

## 7. Shadows & Elevation

Le système d'élévation est double : une ombre portée douce pour la profondeur, et un glow coloré pour l'aspect premium.

| Niveau | Shadow X | Shadow Y | Blur | Spread | Opacity | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Elevation 0** | 0 | 0 | 0 | 0 | 0% | Éléments plats |
| **Elevation 1** | 0 | `4px` | `12px` | 0 | `10%` | Cartes simples |
| **Elevation 2** | 0 | `8px` | `24px` | 0 | `20%` | Cartes en avant-plan, dropdowns |
| **Elevation 3 (Glow)** | 0 | `0` | `32px` | `0` | `30-40%` | Effet néon derrière les cartes à données (violet, vert) |

**Glassmorphism Spécification :**
*   **Background Opacity :** `70%`
*   **Blur :** `20px` (backdrop-filter)
*   **Border :** `1px solid rgba(255,255,255,0.08)`
*   **Saturation :** `180%` (pour accentuer les couleurs filtrées)

---

## 8. Layout System

*   **Largeur maximale du contenu :** `1240px` (centré).
*   **Grille :** 12 colonnes responsive.
*   **Gutters :** `24px`.
*   **Marges :** `24px` (Desktop), `16px` (Tablet), `12px` (Mobile).
*   **Header :** Navigation horizontale (Logo à gauche, Nav au centre, Action à droite).
*   **Sidebar :** Absente. L'interface utilise une navigation en haut.
*   **Main Content :** Organisation en grille de cartes (2 colonnes pour les petites cartes de stats, 1 colonne large pour les graphiques et cartes larges).
*   **Responsive :**
    *   **Mobile :** Tout passe en 1 colonne.
    *   **Tablet :** Grille 2 colonnes.
    *   **Desktop :** Grille complète 3 colonnes (ex: Current Balance, Total Savings, Payment Success Rate sur la même rangée).

---

## 9. Components

### Button
*   **Height :** `48px` (Button Large), `40px` (Button Medium).
*   **Padding :** `16px` horizontal, `8px` vertical.
*   **Radius :** `radius.full` (Pilule) pour les boutons principaux.
*   **Typography :** Button (14px, Medium).
*   **Icon size :** `20px`.
*   **Gap :** `8px`.
*   **Background :**
    *   **Primary :** `color.primary` (Violet).
    *   **Secondary :** Transparent ou `rgba(255,255,255,0.05)`.
*   **Border :** Aucun (Primary), 1px border (Secondary).
*   **Shadow :** Léger glow violet pour les primaires.
*   **States :**
    *   **Default :** Violet plein.
    *   **Hover :** Violet plus clair (`#9D74F8`).
    *   **Active :** Violet plus foncé.
    *   **Focus :** Outline violet double.
    *   **Disabled :** Opacité réduite (50%).

### Input
*   **Height :** `48px`.
*   **Padding :** `12px` horizontal, `16px` vertical.
*   **Radius :** `radius.md` (12px).
*   **Border :** `1px solid rgba(255,255,255,0.08)`.
*   **Typography :** Input Text (16px).
*   **Placeholder :** `color.text.muted`.
*   **Icon :** Icône de recherche ou filtres à gauche/droite.
*   **Focus State :** Bordure primaire (`color.primary`).
*   **Error State :** Bordure `color.error`.
*   **Disabled State :** Fond grisé, opacité 60%.

### Card
*   **Background :** `color.surface.glass`.
*   **Border :** `1px solid color.border`.
*   **Radius :** `radius.xl` (24px).
*   **Shadow :** `shadow.md` + `shadow.lg` (glow) si la carte contient des données clés.
*   **Padding :** `24px`.
*   **Internal Spacing :** `16px` entre les éléments internes.

### Autres composants analysés
*   **Navigation :** Tabs horizontales, actif en pilule violette.
*   **Badges :** Forme pilule, fond sombre, texte clair (ex: "Scheduled").
*   **Avatars :** Ronds, avec des photos.
*   **Tabs :** Pilules avec fond violet pour l'état actif, transparent pour l'inactif.
*   **Graphiques :** Barres (Cash Flow) et circulaires (Payment Success Rate) avec des bordures épaisses et des effets glow.
*   **Listes (Transactions) :** Chaque ligne contient un avatar, un nom, une date et un montant (vert/rouge). Les lignes sont séparées par des dividers subtils.
*   **Progress Indicators :** Cercles de progression (ex: 50%, 75%) avec des traits épais et colorés.

---

## 10. Iconography

*   **Style :** Outline (contour), trait fin, coins arrondis (style "Poppins" ou "Lucide").
*   **Stroke Width :** `1.5px` à `2px` (léger et net).
*   **Corner style :** Arrondi.
*   **Size :** `20px` (souvent pour les boutons), `24px` (pour les icônes de navigation).
*   **Optical weight :** Proportionné au texte environnant.
*   **Alignment :** Centré verticalement et horizontalement avec le texte.
*   **Bibliothèque :** Utilisation d'une bibliothèque d'icônes cohérente et professionnelle, comme **Lucide Icons** ou **Phosphor Icons** (style Regular/Thin).
*   **Couleurs :** Les icônes sont monochromes. Elles héritent de la couleur du texte environnant (`color.text.secondary` ou `color.text.primary`) ou de la couleur primaire pour les actions.

---

## 11. States

| État | Définition |
| :--- | :--- |
| **Default** | Apparence normale, telle que définie dans les composants. |
| **Hover** | Léger changement de couleur de fond ou d'opacité (ex: 10% de blanc en plus). |
| **Focus** | Outline violette autour de l'élément (bouton, input). |
| **Active** | Légèrement plus foncé que le hover (simule un appui). |
| **Selected** | Pillule violette pleine pour les onglets, fond légèrement plus clair pour les listes. |
| **Disabled** | Opacité réduite (50%) et curseur interdit. |
| **Loading** | Icône spinner remplaçant le contenu. |
| **Success** | Texte/Valeur en vert (`color.success`). |
| **Warning** | Texte/Valeur en jaune (`color.warning`). |
| **Error** | Texte/Valeur en rouge (`color.error`). |

---

## 12. Figma Variables / Tokens

### Colors
*   `color.background.primary`
*   `color.surface.primary`
*   `color.surface.glass`
*   `color.text.primary`
*   `color.text.secondary`
*   `color.text.muted`
*   `color.primary`
*   `color.success`
*   `color.warning`
*   `color.error`
*   `color.border`

### Typography
*   `font.family.primary` (Inter)
*   `font.size.body` (16px)
*   `font.size.h1` (32px)
*   `font.weight.regular` (400)
*   `font.weight.medium` (500)
*   `font.weight.bold` (700)

### Spacing
*   `spacing.xs` (4px)
*   `spacing.sm` (8px)
*   `spacing.md` (16px)
*   `spacing.lg` (24px)
*   `spacing.xl` (32px)
*   `spacing.2xl` (48px)

### Radius
*   `radius.sm` (8px)
*   `radius.md` (12px)
*   `radius.lg` (16px)
*   `radius.xl` (24px)
*   `radius.full` (9999px)

### Shadows
*   `shadow.sm`
*   `shadow.md`
*   `shadow.glow.purple`
*   `shadow.glow.green`

---

## 13. Design Principles

1.  **Immersif et Sophistiqué :** Le Dark Mode profond associé à des halos lumineux colorés (glows) crée une atmosphère premium et immersive centrée sur les données.
2.  **Générosité des Espaces :** Utiliser des paddings internes et des gaps généreux (16px à 24px minimum) pour éviter toute sensation d'encombrement et améliorer la lisibilité des données complexes.
3.  **Formes Douces et Accueillantes :** Privilégier les coins très arrondis (Radius XL/Full) pour adoucir l'aspect technique des données financières.
4.  **Contraste Maîtrisé :** Texte blanc éclatant sur fond sombre, avec un texte secondaire gris doux pour hiérarchiser l'information.
5.  **Glassmorphism Subtile :** Utiliser la transparence et le flou d'arrière-plan avec parcimonie (sur les cartes) pour créer de la profondeur sans dégrader la lisibilité.
6.  **Couleurs Sémantiques :** Les couleurs (Vert/ Jaune / Rouge) sont strictement réservées aux indicateurs de tendances (hausse/baisse) et aux états, renforçant la compréhension immédiate.
7.  **Épurer les Bordures :** Réduire au minimum les bordures visibles. Utiliser des fonds légèrement différents pour délimiter les zones plutôt que des lignes dures, pour un rendu plus fluide.
8.  **Toucher de Néon pour les Données Clés :** Utiliser les effets de lueur (glow) et les dégradés de couleurs pour attirer l'œil sur les chiffres financiers les plus importants et les graphiques.