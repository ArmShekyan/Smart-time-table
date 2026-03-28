elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական (Gemini 2.5)")
        st.caption(f"Բարև, **{st.session_state.username}**! Ես քո անձնական AI օգնականն եմ։")

        current_user = st.session_state.username
        if current_user not in st.session_state.chat_histories:
            st.session_state.chat_histories[current_user] = []

        if "pending_proposal" not in st.session_state:
            st.session_state.pending_proposal = None

        # 1. Ցուցադրում ենք չատի պատմությունը
        for message in st.session_state.chat_histories[current_user]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 2. Առաջարկի կոճակը (երբ pending_proposal-ը դատարկ չէ)
        if st.session_state.pending_proposal:
            with st.chat_message("assistant"):
                st.warning("💡 AI-ն ունի առաջարկ։ Ցանկանու՞մ եք տեսնել փոփոխված տարբերակը։")
                
                col_yes, col_no = st.columns(2)
                
                if col_yes.button("✅ Կիրառել (Տեսնել նոր աղյուսակը)", use_container_width=True):
                    proposal_text = st.session_state.pending_proposal
                    st.session_state.pending_proposal = None
                    
                    with st.spinner("🧠 Գեներացվում է նոր աղյուսակը..."):
                        try:
                            context = "Դու 'Smart Time Table' պրոյեկտի AI օգնականն ես։\n"
                            context += "Օգտատերը ՀԱՄԱՁԱՅՆԵՑ քո առաջարկին։ Հիմա արա այդ փոփոխությունը և արդյունքը ցույց տուր ՏԵՔՍՏԱՅԻՆ ՀՈՐԻԶՈՆԱԿԱՆ ԱՂՅՈՒՍԱԿՈՎ (Markdown table)։\n"
                            context += "Աղյուսակում տողերը պետք է լինեն ԺԱՄԵՐԸ (1, 2, 3...), իսկ սյունակները՝ ՕՐԵՐԸ (Երկուշաբթի, Երեքշաբթի...)։\n"
                            
                            if st.session_state.schedule:
                                context += f"Նախնական դասացուցակը՝ {json.dumps(st.session_state.schedule, ensure_ascii=False)}\n"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=context + f"\nՔո նախորդ առաջարկը, որին համաձայնեցին՝ {proposal_text}",
                            )
                            response_text = response.text

                            st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Սխալ: {str(e)}")

                if col_no.button("❌ Չեղարկել", use_container_width=True):
                    st.session_state.pending_proposal = None
                    st.toast("Առաջարկը չեղարկվեց", icon="🗑️")
                    st.rerun()

        # 3. Օգտատիրոջ նոր հարցը
        if prompt := st.chat_input("Ինչպե՞ս կարող եմ օգնել քեզ այսօր։"):
            # Մաքրում ենք հին առաջարկը նոր հարցի դեպքում
            st.session_state.pending_proposal = None 
            
            st.session_state.chat_histories[current_user].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🧠 Մտածում եմ..."):
                    try:
                        if "GEMINI_API_KEY" not in st.secrets:
                            response_text = "⚠️ API բանալին բացակայում է Streamlit Cloud-ի Secrets-ից:"
                        else:
                            # Փորձագիտական կոնտեքստ
                            context = "Դու 'Smart Time Table' պրոյեկտի փորձագետ AI օգնականն ես։\n"
                            context += f"Դու խոսում ես {current_user}-ի հետ։\n"
                            context += "⚠️ ՔՈ ԳԼԽԱՎՈՐ ԿԱՆՈՆՆԵՐԸ (Expert Rules):\n"
                            context += "1. ℹ️ ՏԵՂԵԿԱՏՈՒ: Հստակ պատասխանիր դասացուցակի մասին հարցերին:\n"
                            context += "2. 🧠 SMART TWEAKS: Ծանր առարկաները (Մաթեմատիկա, Ֆիզիկա) 1-3 ժամերին, ուսուցչին օրական մաքսիմում 5 դաս:\n"
                            context += "3. 💡 ԱՌԱՋԱՐԿ: Միանգամից աղյուսակ մի՛ ցույց տուր: Ասա, որ օգտատերը կարող է սեղմել 'Կիրառել' կոճակը:\n"

                            if st.session_state.schedule:
                                context += f"Ներկայիս դասացուցակը՝ {json.dumps(st.session_state.schedule, ensure_ascii=False)}\n"
                                if "teachers" in st.session_state:
                                    # Ուղղում ենք Teacher object-ի սխալը str() դարձնելով
                                    context += f"Ուսուցիչների բազան՝ {str(st.session_state.teachers)}\n"
                            else:
                                context += "Դեռևս գեներացված դասացուցակ չկա։\n"

                            context += f"Օգտատիրոջ հարցը՝ {prompt}"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', 
                                contents=context,
                            )
                            response_text = response.text

                            # Ցուցադրում և պահպանում
                            st.markdown(response_text)
                            st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})

                            # Ստուգում ենք՝ արդյոք կա առաջարկ, որպեսզի կոճակը հայտնվի
                            trigger_words = ["առաջարկ", "փոխել", "տեղափոխ", "swap", "լավացնել"]
                            if any(word in response_text.lower() for word in trigger_words):
                                st.session_state.pending_proposal = response_text
                                st.rerun()

                    except Exception as e:
                        st.error(f"❌ Սխալ API կանչի ժամանակ: {str(e)}")
