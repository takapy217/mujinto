import streamlit as st
import json
import re
import time

# JSON読み込み関数
def load_story(lang):
    filename = "story_mujinto_en.json" if lang == "en" else "story_mujinto_jp.json"
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# セッション初期化
def init_session():
    defaults = {
        "chapter": "start",
        "lp": 100,
        "selected": None,
        "show_result": False,
        "show_next": False,
        "show_story": False,
        "player_name": "",
        "lang": "ja",
        "show_choices": False,
        "lp_updated": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# プレイヤーネームを埋め込む
def personalize(text):
    name = st.session_state.get("player_name", "あなた")
    return re.sub(r"{player_name}", name, text or "")

# メイン処理
def main():
    st.set_page_config(page_title="無人島脱出アドベンチャー/Deserted Island Escape Adventure", layout="centered")
    init_session()

    story = load_story(st.session_state.lang)
    chapter_key = st.session_state.chapter

    if st.session_state.chapter == "start":
        lang_map = {"日本語": "ja", "English": "en"}
        lang_selection = st.radio("🌐 Language / 言語を選んでください：", ("日本語", "English"), index=0)
        st.session_state.lang = lang_map[lang_selection]
        lang = st.session_state.lang

        story = load_story(lang)
        st.image("assets/img_start.png", use_container_width=True)
        st.markdown("❤️ LP: " + str(st.session_state.lp))
        st.markdown("無人島脱出アドベンチャー/Deserted Island Escape Adventure")



        if st.button("▶ ゲームを始める / Game start"):
                st.session_state.chapter = "1"
                st.rerun()

        intro_text = story.get("intro_text", "")
        st.markdown(personalize(intro_text))


        st.stop()

    story = load_story(st.session_state.lang)
    chapter = story["chapters"].get(st.session_state.chapter)
    if not chapter:
        st.error("この章のデータが見つかりません")
        return

    if st.session_state.lp <= 0:
        st.markdown("### 💀  Game Over")
        st.image("assets/img_gameover.png", use_container_width=True)

        if st.button("🔁 最初からやり直す / Restart"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    # 結果表示フェーズ
    if st.session_state.show_result and st.session_state.selected is not None:
        choice = chapter["choices"][st.session_state.selected]
        result_data = choice["result"]
        result = personalize(result_data.get("text", ""))

        if not st.session_state.lp_updated:
            lp_diff = result_data.get("lp", 0)
            st.session_state.lp = max(0, min(100, st.session_state.lp + lp_diff))
            st.session_state.lp_updated = True


        result_image = result_data.get("result_image", chapter.get("choice_image", chapter["image"]))
        st.image(f"assets/{result_image}", use_container_width=True)
        st.markdown("❤️ LP: " + str(st.session_state.lp))
        st.write(result)

        button_label_n = result_data.get("button_label_n", "▶ 次へ / Next")

        if choice.get("correct", False):
            if st.button(personalize(button_label_n)):
                st.session_state.chapter = str(result_data.get("next", "end"))
                st.session_state.selected = None
                st.session_state.show_result = False
                st.session_state.show_story = False
                st.session_state.show_choices = False
                st.session_state.lp_updated = False
                st.rerun()
        else:
            if st.button("▶ 他を試してください / Choose Again"):
                st.session_state.show_result = False
                st.session_state.selected = None
                st.session_state.lp_updated = False
                st.rerun()
        return

    st.image(f"assets/{chapter.get('image')}", use_container_width=True)
    st.markdown("❤️ LP: " + str(st.session_state.lp))
    st.write(personalize(chapter.get("text", "")))

    # 選択肢をすぐ表示（choices）
    if not chapter.get("choices"):
        st.markdown("Thank you for playing!")
        if st.button("🔙 スタート画面に戻る / Back to start"):
            st.balloons()
            time.sleep(2)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    for i, choice in enumerate(chapter["choices"]):
        if st.button(personalize(choice["text"]), key=f"choice_{i}"):
            st.session_state.selected = i
            st.session_state.show_result = True
            st.session_state.lp_updated = False
            st.rerun()
    return  # ← このreturnが重要

    st.image(f"assets/{chapter.get('choice_image', chapter['image'])}", use_container_width=True)
    st.markdown("❤️ LP: " + str(st.session_state.lp))
    if not chapter.get("choices"):
        st.markdown("Thank you for playing!")
        if st.button("🔙 スタート画面に戻る / Back to start"):
            st.balloons()
            time.sleep(2)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    for i, choice in enumerate(chapter["choices"]):
        if st.button(personalize(choice["text"]), key=f"choice_{i}"):
            st.session_state.selected = i
            st.session_state.show_result = True
            st.session_state.lp_updated = False
            st.rerun()

if __name__ == "__main__":
    main()