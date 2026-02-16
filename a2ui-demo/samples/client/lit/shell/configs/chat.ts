/*
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

import { AppConfig } from "./types.js";

export const config: AppConfig = {
  key: "chat",
  title: "Chat App",
  placeholder: "Type a message...",
  loadingText: "Thinking...",
  serverUrl: "http://localhost:10004",
  background: `linear-gradient(
    135deg,
    light-dark(#f5f3ff, #1e1b4b) 0%,
    light-dark(#ede9fe, #312e81) 100%
  )`,
};
