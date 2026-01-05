# Deployment zu schamborski.com

## ✅ Bereits erledigt:
- CNAME Datei mit `schamborski.com` wurde erstellt

## 📋 Nächste Schritte:

### 1. GitHub Pages aktivieren
1. Gehe zu deinem GitHub Repository: https://github.com/[dein-username]/Nickii-Schamborski
2. Klicke auf **Settings** (Einstellungen)
3. Scrolle runter zu **Pages** (im linken Menü)
4. Unter **Source** wähle: **Deploy from a branch**
5. Branch: **main** (oder **master**), Folder: **/ (root)**
6. Klicke **Save**

### 2. DNS-Einstellungen bei deinem Domain-Provider
Gehe zu deinem Domain-Provider (wo du schamborski.com gekauft hast) und füge folgende DNS-Einträge hinzu:

**A-Records:**
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**CNAME-Record (optional für www):**
```
www  →  [dein-github-username].github.io
```

### 3. Warten (15 Min - 24 Std)
DNS-Änderungen können bis zu 24 Stunden dauern, sind aber meist nach 15 Minuten aktiv.

### 4. HTTPS aktivieren
Zurück auf GitHub → Settings → Pages:
- Setze Haken bei **Enforce HTTPS**

## ✅ Fertig!
Deine Website ist dann unter https://schamborski.com erreichbar!

## 🔄 Updates veröffentlichen
Immer wenn du etwas änderst:
```bash
git add .
git commit -m "Update content"
git push origin main
```

Die Änderungen sind nach 1-2 Minuten live!
