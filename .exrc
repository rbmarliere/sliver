lua << EOF
require("lspconfig").pylsp.setup({
  -- organizeImports requires pylsp-rope in mason env
  on_attach = LSPAttach,
  capabilities = LSPCapabilities,
  settings = {
    pylsp = {
      plugins = {
        mccabe = {
          threshold = 20,
        },
      },
    },
  },
})

require("dap").adapters.chrome = {
  type = "executable",
  command = "node",
  args = { vim.fn.stdpath("data") .. "/mason/packages/chrome-debug-adapter/out/src/chromeDebug.js" },
}
require("dap").configurations.typescript = {
  {
    type = "chrome",
    request = "attach",
    program = "${file}",
    cwd = vim.fn.getcwd(),
    sourceMaps = true,
    protocol = "inspector",
    port = 9222,
    webRoot = "${workspaceFolder}/web",
  },
}

local cfg = function(config, on_config)
  local final_config = vim.deepcopy(config)
  final_config.justMyCode = false
  on_config(final_config)
end;

require("dap").adapters.serve = {
  type = "server";
  port = 33333;
  enrich_config = cfg;
}
require("dap").adapters.stream = {
  type = "server";
  port = 33334;
  enrich_config = cfg;
}
require("dap").adapters.watch = {
  type = "server";
  port = 33335;
  enrich_config = cfg
}

require("dap").configurations.python = {
  {
    type = "serve",
    request = "attach",
    name = "Serve",
  },
  {
    type = "stream",
    request = "attach",
    name = "Stream",
  },
  {
    type = "watch",
    request = "attach",
    name = "Watch",
  },
}
EOF
