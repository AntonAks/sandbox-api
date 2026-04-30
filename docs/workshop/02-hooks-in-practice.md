# 02 — Hooks на практиці

> Навчальна замітка. Тема: як на практиці налаштувати три типи хуків на цьому проекті, і яка філософія за кожним.

## Шари захисту: prompt, hook, CI

Перед тим як говорити про конкретику — важливий принцип. Запобігання помилкам в AI-збагаченому процесі **повинно бути пошаровим**. Один шар → один точок відмови:

| Шар | Що це | Гарантія | Вартість |
|-----|-------|----------|----------|
| 1. Prompt-level (CLAUDE.md, code rules) | Інструкції для LLM | **Soft** — LLM "пам'ятає" і намагається. Може забути. | Безкоштовно. Інстант-feedback, але крихка. |
| 2. Hook-level (`.claude/settings.json`) | Shell-команда від harness на event | **Hard** локально — спрацює навіть якщо LLM забув. | Невелика — кілька хвилин на хук. Локальна (працює тільки в Claude Code). |
| 3. CI-level (`ci.yml`) | Перевірка в pipeline | **Hard** глобально — блокує merge. | Помірна. Працює для всіх, не тільки для AI. |

**Не покладайся на один шар.** Prompt — щоб LLM "знав і поважав". Hook — щоб виправляв одразу. CI — щоб не пропустити в main навіть якщо хук обійдено.

## Що ми налаштували в цьому репо

Файл: `.claude/settings.json`. Активних хуків: 3.

### Хук 1: Auto-format (`PostToolUse` Edit/Write/MultiEdit)

**Ціль:** після кожного редагування `.py` файла автоматично прогнати `ruff format` + `ruff check --fix`. Я не маю шансу залишити файл "брудним" — навіть якщо забув про стиль, harness прибере.

**Команда (інлайн в settings.json):**
```bash
jq -r '.tool_response.filePath // .tool_input.file_path' \
  | { read -r f; case "$f" in *.py) uvx --quiet ruff format "$f" && uvx --quiet ruff check --fix "$f" ;; esac; } \
  2>/dev/null || true
```

**Розбір:**
- `jq` витягує шлях до файла з JSON-payload, який harness кидає на stdin.
- `case ... *.py)` — фільтр, щоб не запускати ruff на не-Python файлах (markdown, json, тощо).
- `uvx ruff` — запускає ruff в ізольованому tool-env через `uv`. Працює навіть коли проект ще не setup-нутий (`.venv` не існує). Кешується.
- `2>/dev/null || true` — хук не повинен падати; якщо ruff недоступний, мовчки пропускаємо.

**Pedagogical takeaway:** "виправляй автоматично" краще ніж "сваритись пост-фактум". Style — це шум, його треба прибирати з мого вікна уваги.

### Хук 2: Detect deprecated patterns (`PostToolUse` Edit/Write/MultiEdit)

**Ціль:** після форматування — просканувати файл на застарілі паттерни (Pydantic v1, SQLAlchemy 1.x, Step-comments). Якщо знайдено — `exit 2` зі stderr-feedback. Я бачу попередження як зворотній зв'язок і виправляю.

**Реалізація:** окремий скрипт `.claude/scripts/check-deprecated.sh`. Чому окремо, не інлайн:
- Список паттернів буде рости — додавати в bash-скрипт легше ніж в JSON-string-with-escaping.
- Скрипт можна запустити вручну для дебагу: `echo '{"tool_input":{"file_path":"x.py"}}' | .claude/scripts/check-deprecated.sh`.
- Settings.json лишається читабельним.

**Що ловить (на старті):**
- `from pydantic import BaseSettings` — v1, переїхало в `pydantic_settings`.
- `from pydantic import validator` / `root_validator` — v1, треба `field_validator` / `model_validator`.
- `from sqlalchemy.ext.declarative import ...` — 1.x, треба `from sqlalchemy.orm import DeclarativeBase`.
- `.query(` — 1.x, треба `select()` + `session.execute()`.
- `uselist=` — 2.0 проектує це через `Mapped[]` типи, не параметр.
- `# Step N:` коментарі — банить style-rule з code_rules.md.

**Як розширювати:** дописати рядок `check 'regex' 'message'` в скрипті. Більше нічого.

**Важливе обмеження:** grep не розуміє Python синтаксис. Якщо паттерн в коментарі або docstring — буде false positive. Прийнятно, бо false positive легко обійти, а false negative (пропущена помилка) — ні.

**Pedagogical takeaway:** PostToolUse + `exit 2` зі stderr — це elegant механізм "м'якого блоку". Я отримую попередження як feedback, можу інтерпретувати і вирішити (виправити vs. залишити). Це не блокує робочий цикл і не вимагає магії.

### Хук 3: Block destructive git ops (`PreToolUse` Bash)

**Ціль:** жорстко блокувати `git push`, `git commit`, `git reset` — навіть в compound-командах типу `cd foo && git push`. Це user-only операції в цьому проекті.

**Команда:**
```bash
cmd=$(jq -r '.tool_input.command')
case "$cmd" in
  *"git push"*|*"git commit"*|*"git reset"*)
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"git push/commit/reset are reserved for the user — run them manually."}}'
    ;;
esac
```

**Розбір:**
- Простий `case`-match по підрядку — стійкіший і кросплатформений за регулярки.
- Якщо матч — повертаємо JSON з `permissionDecision: deny` + reason. Harness блокує виклик і показує мені reason як feedback.
- Якщо не матч — `case` нічого не виводить, `exit 0`, harness пропускає.

**Чому substring а не regex:**
- `git push` буде підрядком в `git push origin main`, `cd foo && git push`, навіть `echo "git push"` — все блокується.
- Останній — false positive (LLM надрукує help-message в bash echo з фразою "git push"). Ціна false positive: один зайвий блок, що відразу видно і легко обійти. Ціна false negative: незаплановане редагування історії git. Невідповідно.

**Pedagogical takeaway:** PreToolUse — це **єдиний** механізм абсолютної гарантії що дія не виконається. Все інше можна обійти або забути. Якщо щось має ОБОВ'ЯЗКОВО не статись — це PreToolUse hook.

## Як перевірити що хуки активні

Каверзна частина: **новий `.claude/settings.json` не підхоплюється посеред сесії**. Watcher Claude Code дивиться тільки за тими каталогами, де файл уже існував на старті. Тому якщо ти створив `settings.json` під час сесії — жодних хуків.

**Способи перевірити:**
1. Відкрий `/hooks` в Claude Code один раз — це перечитає конфіг.
2. Або просто перезапусти Claude Code.
3. Перевірити що працює: попроси мене створити `.py` файл з deprecated паттерном (наприклад, `from pydantic import BaseSettings`). Якщо хук активний — побачиш stderr-warning і автоматичне виправлення; якщо ні — файл збережеться "як є".

## Pre-flight checklist (для презентації)

Якщо демонструєш hook setup на воркшопі:

1. Покажи `.claude/settings.json` — структуру (`PostToolUse` / `PreToolUse`, `matcher`, масив `hooks`).
2. Покажи скрипт `.claude/scripts/check-deprecated.sh` — як легко розширювати list of patterns.
3. Запусти live: попроси Claude створити файл з `BaseSettings` (v1) — покажи feedback від хука і автоматичне виправлення на `pydantic_settings.BaseSettings`.
4. Спробуй `git push` — покажи що блокується перед виконанням.
5. Поясни обмеження: cache, watcher, false positives.

## Чого ми НЕ зробили (свідомо)

- **CI-level grep checks** на застарілі паттерни — додамо коли будемо налаштовувати GHA. Це третій шар, окремо від хука.
- **Ruff config з `UP` group в pyproject.toml** — додамо коли проект буде сетапитись.
- **Скіл-рівень "review checklist"** — поки не треба, бо хуки + правила покривають основне.

Це свідома послідовність: ми ставимо grep-хук **до** того як в проекті з'являється Python код, щоб коли я почну писати — вже мав live-feedback. CI grep-check додамо паралельно з самим CI workflow в spec.md.
