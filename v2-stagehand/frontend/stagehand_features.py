import streamlit as st
import json
import base64
from typing import Dict
from io import BytesIO
from datetime import datetime


class StagehandFeaturesUI:
    def __init__(self, api_client):
        self.api = api_client

    def render(self):
        st.header("Stagehand AI Features")

        tab1, tab2, tab4 = st.tabs([
            "Quick Action",
            "Agent Workflow",
            #"Extract Data",
            "Multi-Step"
        ])

        with tab1:
            self._render_quick_action()

        with tab2:
            self._render_agent_workflow()

        # with tab3:
        #     self._render_extraction()

        with tab4:
            self._render_multistep()

    def _render_quick_action(self):
        st.subheader("Quick Action - Observe & Act")

        st.info("""
        **Best for:** Single, atomic actions
        - "Click the sign in button"
        - "Find me list of the phones sold in year 2018"
        - NOT: "Sign in to the website" (too complex)
        """)

        # Clear results button
        if st.session_state.get('last_result_type') == "Action" and 'last_result' in st.session_state:
            if st.button("🗑️ Clear Results", key="clear_action_results"):
                if 'last_result' in st.session_state:
                    del st.session_state['last_result']
                if 'last_result_type' in st.session_state:
                    del st.session_state['last_result_type']
                st.rerun()

        with st.form("quick_action_form"):
            url = st.text_input("Target URL", placeholder="https://example.com")
            instruction = st.text_area(
                "Instruction",
                placeholder="Click the sign in button",
                height=80
            )

            col1, col2 = st.columns(2)
            with col1:
                draw_overlay = st.checkbox("Show Visual Overlay", value=False)
            with col2:
                take_screenshots = st.checkbox("Take Screenshots", value=True)

            submitted = st.form_submit_button("Execute", width='stretch')

            if submitted and url and instruction:
                with st.spinner("Executing action..."):
                    result = self.api.stagehand_action(url, instruction, draw_overlay, take_screenshots)
                    if result:
                        st.session_state['last_result'] = result
                        st.session_state['last_result_type'] = "Action"
                        st.rerun()

        # Display persisted results (after form, outside of submission)
        if st.session_state.get('last_result_type') == "Action" and 'last_result' in st.session_state:
            self._display_result(st.session_state['last_result'], "Action")

    def _render_agent_workflow(self):
        st.subheader("Agent Workflow - Autonomous Execution")

        st.info("""
        **Best for:** Complex multi-step tasks
        - "Navigate to products and filter by Electronics"
        - "Search for AI automation and click first result"
        - "Apply to first job posting with mock data"
        """)

        # Clear results button
        if st.session_state.get('last_result_type') == "Workflow" and 'last_result' in st.session_state:
            if st.button("🗑️ Clear Results", key="clear_workflow_results"):
                if 'last_result' in st.session_state:
                    del st.session_state['last_result']
                if 'last_result_type' in st.session_state:
                    del st.session_state['last_result_type']
                st.rerun()

        with st.form("agent_workflow_form"):
            url = st.text_input("Starting URL", placeholder="https://example.com")
            instruction = st.text_area(
                "Workflow Instructions",
                placeholder="Navigate to products page and filter by Electronics",
                height=100
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                max_steps = st.number_input("Max Steps", 1, 100, 20)
            with col2:
                auto_screenshot = st.checkbox("Auto Screenshot", value=True)
            with col3:
                wait_between = st.number_input("Wait (ms)", 0, 10000, 1000, 100)

            submitted = st.form_submit_button("Execute Workflow", width='stretch')

            if submitted and url and instruction:
                with st.spinner("Executing workflow... This may take a while."):
                    result = self.api.stagehand_workflow(url, instruction, max_steps, auto_screenshot, wait_between)
                    if result:
                        st.session_state['last_result'] = result
                        st.session_state['last_result_type'] = "Workflow"
                        st.rerun()

        # Display persisted results (after form, outside of submission)
        if st.session_state.get('last_result_type') == "Workflow" and 'last_result' in st.session_state:
            self._display_result(st.session_state['last_result'], "Workflow")

    def _render_extraction(self):
        st.subheader("Extract Data - Structured Extraction")

        schemas_response = self.api.get_stagehand_schemas()

        if isinstance(schemas_response, list):
            schemas = {schema.get('name', f'schema_{i}'): schema for i, schema in enumerate(schemas_response)}
        elif isinstance(schemas_response, dict):
            schemas = schemas_response
        else:
            schemas = {}

        if not schemas:
            st.warning("No extraction schemas available. Please configure schemas in the backend.")
            st.info("You can still use the 'Quick Action' or 'Agent Workflow' tabs for extraction without predefined schemas.")
            return

        with st.form("extraction_form"):
            url = st.text_input("Target URL", placeholder="https://example.com/product")

            schema_name = st.selectbox(
                "Data Schema",
                options=list(schemas.keys()),
                format_func=lambda x: f"{x} - {schemas.get(x, {}).get('description', 'N/A')}"
            )

            if schema_name and schema_name in schemas:
                with st.expander("Schema Fields", expanded=False):
                    schema_fields = schemas[schema_name].get('fields', [])

                    if isinstance(schema_fields, list):
                        if schema_fields:
                            st.write("**Fields:**")
                            for field in schema_fields:
                                if isinstance(field, str):
                                    st.write(f"• **{field}**")
                                elif isinstance(field, dict):
                                    field_name = field.get('name', 'unknown')
                                    field_desc = field.get('description', '')
                                    required = "[Required]" if field.get('required') else "[Optional]"
                                    st.write(f"{required} **{field_name}**: {field_desc}")
                        else:
                            st.write("No field details available for this schema.")

                    elif isinstance(schema_fields, dict):
                        if schema_fields:
                            for field, info in schema_fields.items():
                                if isinstance(info, dict):
                                    required = "[Required]" if info.get('required') else "[Optional]"
                                    st.write(f"{required} **{field}**: {info.get('description', 'N/A')}")
                                else:
                                    st.write(f"• **{field}**: {info}")
                        else:
                            st.write("No field details available for this schema.")

                    else:
                        st.write("No field details available for this schema.")

            instruction = st.text_area(
                "Extraction Instructions",
                placeholder="Extract product name, price, and rating",
                height=80
            )

            take_screenshots = st.checkbox("Take Screenshots", value=True)

            submitted = st.form_submit_button("Extract Data", width='stretch')

        if submitted and url and instruction and schema_name:
            with st.spinner("Extracting data..."):
                result = self.api.stagehand_extract(url, instruction, schema_name, take_screenshots)
                if result:
                    self._display_result(result, "Extraction")

    def _render_multistep(self):
        st.subheader("Multi-Step Workflow - Sequential Instructions")

        st.info("""
        **Build step-by-step workflows.** Keep each step atomic!
        - The workflow automatically navigates to your Target URL
        - Step 1: "Click filters button"
        - Step 2: "Select Electronics category"
        - NOT: "Open filters and select Electronics" (too complex for one step)
        
        """)

        if 'multistep_instructions' not in st.session_state:
            st.session_state.multistep_instructions = []

        if 'bulk_step_buffer' not in st.session_state:
            st.session_state.bulk_step_buffer = [{
                "instruction_type": "observe",
                "instruction_text": "",
                "wait_after": 2000
            }]

        # Clear results button
        if st.session_state.get('last_result_type') == "Multi-Step" and 'last_result' in st.session_state:
            if st.button("🗑️ Clear Results", key="clear_multistep_results"):
                if 'last_result' in st.session_state:
                    del st.session_state['last_result']
                if 'last_result_type' in st.session_state:
                    del st.session_state['last_result_type']
                st.rerun()

        col1, col2 = st.columns([3, 1])
        with col1:
            url = st.text_input("Target URL", value="https://example.com", key="multistep_url")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Clear All"):
                st.session_state.multistep_instructions = []
                st.rerun()

        with st.expander("Add Steps", expanded=True):
            st.caption("Add multiple steps at once. Leave instruction blank to skip a row.")
            column_config = {
                "instruction_type": st.column_config.SelectboxColumn(
                    "Step Type",
                    options=["observe", "act", "extract", "wait", "screenshot"],
                    default="observe",
                    required=True
                ),
                "instruction_text": st.column_config.TextColumn(
                    "Instruction",
                    help="Provide a natural-language instruction for the selected step type",
                    required=True
                ),
                "wait_after": st.column_config.NumberColumn(
                    "Wait after (ms)",
                    min_value=0,
                    max_value=10000,
                    step=500,
                    default=2000
                )
            }

            bulk_data = st.data_editor(
                st.session_state.bulk_step_buffer,
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                key="bulk_step_editor"
            )
            st.session_state.bulk_step_buffer = bulk_data

            action_col, reset_col = st.columns(2)
            with action_col:
                add_steps = st.button("Add Listed Steps", type="primary", use_container_width=True)
            with reset_col:
                reset_buffer = st.button("Reset List", use_container_width=True)

            if reset_buffer:
                st.session_state.bulk_step_buffer = [{
                    "instruction_type": "observe",
                    "instruction_text": "",
                    "wait_after": 2000
                }]
                st.rerun()

            if add_steps:
                valid_rows = []
                for row in bulk_data:
                    if not row:
                        continue
                    instruction_text = (row.get("instruction_text") or "").strip()
                    if not instruction_text:
                        continue
                    valid_rows.append({
                        "instruction_type": row.get("instruction_type") or "observe",
                        "instruction_text": instruction_text,
                        "wait_after": int(row.get("wait_after") or 2000)
                    })

                if not valid_rows:
                    st.warning("No valid steps to add. Provide at least one instruction.")
                else:
                    start_index = len(st.session_state.multistep_instructions)
                    for idx, row in enumerate(valid_rows, start=1):
                        st.session_state.multistep_instructions.append({
                            "step_number": start_index + idx,
                            "instruction_type": row["instruction_type"],
                            "instruction_text": row["instruction_text"],
                            "wait_after": row["wait_after"]
                        })
                    st.session_state.bulk_step_buffer = [{
                        "instruction_type": "observe",
                        "instruction_text": "",
                        "wait_after": 2000
                    }]
                    st.success(f"Added {len(valid_rows)} step(s)!")
                    st.rerun()

        if st.session_state.multistep_instructions:
            st.divider()
            st.subheader(f"Workflow Steps ({len(st.session_state.multistep_instructions)})")

            for idx, step in enumerate(st.session_state.multistep_instructions):
                col1, col2, col3, col4 = st.columns([0.5, 1.5, 5, 1])

                with col1:
                    st.markdown(f"**{step['step_number']}**")
                with col2:
                    st.markdown(f"`{step['instruction_type']}`")
                with col3:
                    st.markdown(f"_{step['instruction_text']}_")
                with col4:
                    if st.button("Delete", key=f"del_{idx}", help="Delete this step"):
                        st.session_state.multistep_instructions.pop(idx)
                        for i, s in enumerate(st.session_state.multistep_instructions):
                            s['step_number'] = i + 1
                        st.rerun()

            st.divider()

            col1, col2, col3 = st.columns(3)
            with col1:
                take_screenshots = st.checkbox("Take screenshots", value=True, key="ms_screenshots")
            with col2:
                draw_overlay = st.checkbox("Draw overlay", value=False, key="ms_overlay")
            with col3:
                stop_on_error = st.checkbox("Stop on error", value=False, key="ms_stop")

            if st.button("Execute Workflow", type="primary", width='stretch'):
                with st.spinner("Executing multi-step workflow..."):
                    result = self.api.stagehand_multistep(
                        url,
                        st.session_state.multistep_instructions,
                        take_screenshots,
                        draw_overlay,
                        stop_on_error
                    )
                    if result:
                        st.session_state['last_result'] = result
                        st.session_state['last_result_type'] = "Multi-Step"
                        st.rerun()

        if st.session_state.get('last_result_type') == "Multi-Step" and 'last_result' in st.session_state:
            self._display_multistep_result(st.session_state['last_result'])

    def _display_result(self, result: Dict, result_type: str):
        st.divider()
        st.subheader(f"{result_type} Results")

        if result.get('success'):
            st.success(f"{result_type} completed successfully!")

            col1, col2 = st.columns(2)
            with col1:
                if 'processing_time' in result:
                    st.metric("Processing Time", f"{result['processing_time']:.2f}s")
            with col2:
                if 'observed_elements' in result:
                    st.metric("Observed Elements", result['observed_elements'])

            if result.get('data'):
                st.write("**Extracted Data:**")
                st.json(result['data'])

            if result.get('result'):
                st.write("**Result:**")
                st.json(result['result'])

            artifacts = result.get('artifacts', [])
            if artifacts:
                st.write("**Screenshots:**")
                for idx, artifact in enumerate(artifacts):
                    if artifact.get('description'):
                        st.write(f"**Description:** {artifact['description']}")
                    if artifact.get('type') == 'screenshot' and artifact.get('data'):
                        try:
                            from PIL import Image
                            img_data = base64.b64decode(artifact['data'])
                            img = Image.open(BytesIO(img_data))

                            with st.expander(f"Screenshot {idx + 1}", expanded=True):
                                st.image(img, caption=f"{result_type} Screenshot", width='stretch')

                                st.download_button(
                                    f"Download Screenshot {idx + 1}",
                                    data=img_data,
                                    file_name=f"{result_type.lower()}_screenshot_{idx + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                    mime="image/png",
                                    key=f"download_screenshot_{result_type}_{idx}"
                                )
                        except Exception as e:
                            st.error(f"Failed to display screenshot: {str(e)}")
                            st.caption("Screenshot data available but could not be displayed")

            st.download_button(
                "Download Results (JSON)",
                data=json.dumps(result, indent=2),
                file_name=f"{result_type.lower()}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.error(f"{result_type} failed: {result.get('error', 'Unknown error')}")

    def _display_multistep_result(self, result: Dict):
        st.divider()
        st.subheader("Multi-Step Workflow Results")

        if result.get("success"):
            st.success("Workflow completed successfully!")
        else:
            st.error("Workflow failed")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Steps", result.get("total_steps", 0))
        with col2:
            st.metric("Completed", result.get("completed_steps", 0))
        with col3:
            total = result.get("total_steps", 1)
            completed = result.get("completed_steps", 0)
            success_rate = (completed / total * 100) if total > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        with col4:
            st.metric("Execution Time", f"{result.get('total_execution_time', 0):.2f}s")

        st.subheader("Step-by-Step Results")

        for step in result.get("steps", []):
            status_icon = "[Success]" if step['success'] else "[Failed]"
            with st.expander(
                f"{status_icon} Step {step['step_number']}: {step['instruction_type']} - {step['instruction_text']}",
                expanded=not step['success']
            ):
                col1, col2 = st.columns([3, 1])

                with col1:
                    if not step['success']:
                        st.error(f"Error: {step.get('error', 'Unknown error')}")

                    if step.get('data'):
                        st.json(step['data'])

                    st.caption(f"Time: {step['execution_time']:.2f}s")

                with col2:
                    if step.get('screenshot'):
                        try:
                            from PIL import Image
                            img_data = base64.b64decode(step['screenshot'])
                            img = Image.open(BytesIO(img_data))
                            st.image(img, caption=f"Step {step['step_number']}", width='stretch')

                            st.download_button(
                                "Download",
                                data=base64.b64decode(step['screenshot']),
                                file_name=f"step_{step['step_number']}_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                mime="image/png",
                                key=f"download_step_{step['step_number']}_screenshot",
                                width='stretch'
                            )
                        except Exception as e:
                            st.error(f"Failed to display screenshot: {str(e)}")
                            st.caption("Screenshot available")

        st.download_button(
            "Download Full Results (JSON)",
            data=json.dumps(result, indent=2),
            file_name=f"multistep_results_{result.get('job_id', 'unknown')}.json",
            mime="application/json"
        )

    def _get_step_placeholder(self, step_type: str) -> str:
        placeholders = {
            "goto": "Go to the products section",
            "observe": "Find the login button",
            "act": "Click the submit button",
            "extract": "Get the product name",
            "wait": "Wait 2 seconds",
            "screenshot": "Capture current state"
        }
        return placeholders.get(step_type, "Enter instruction...")

    def _get_step_help(self, step_type: str) -> str:
        help_texts = {
            "goto": "Navigate to an URL",
            "observe": "Observe elements before acting on them",
            "act": "Perform an action (click, type, select)",
            "extract": "Extract data from the page",
            "wait": "Wait for a specified time",
            "screenshot": "Capture a screenshot"
        }
        return help_texts.get(step_type, "")

