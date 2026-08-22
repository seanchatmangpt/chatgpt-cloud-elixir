defmodule ChatGPTCloud.ProcessIntelligence do
  use Ash.Domain, extensions: [AshAdmin.Domain]

  admin do
    show? true
  end

  resources do
    resource ChatGPTCloud.ProcessIntelligence.Agent
    resource ChatGPTCloud.ProcessIntelligence.Run
    resource ChatGPTCloud.ProcessIntelligence.Event
    resource ChatGPTCloud.ProcessIntelligence.Object
    resource ChatGPTCloud.ProcessIntelligence.EventObject
    resource ChatGPTCloud.ProcessIntelligence.ObjectObject
    resource ChatGPTCloud.ProcessIntelligence.Receipt
    resource ChatGPTCloud.ProcessIntelligence.ConformanceResult
    resource ChatGPTCloud.ProcessIntelligence.Refusal
    resource ChatGPTCloud.ProcessIntelligence.ProcessVariant
  end
end
