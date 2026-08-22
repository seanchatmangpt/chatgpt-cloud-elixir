defmodule ChatGPTCloud.ProcessIntelligence do
  @moduledoc "Ash-native control and projection domain for process-intelligence evidence."

  use Ash.Domain,
    extensions: [AshAdmin.Domain, AshJsonApi.Domain, AshGraphql.Domain, AshAi]

  admin do
    show? true
  end

  json_api do
    routes do
      base_route "/qualifications", ChatGPTCloud.ProcessIntelligence.Qualification do
        get :read
        index :read
      end

      base_route "/cost-observations", ChatGPTCloud.ProcessIntelligence.CostObservation do
        get :read
        index :read
      end
    end
  end

  graphql do
    queries do
      get ChatGPTCloud.ProcessIntelligence.Qualification, :qualification, :read
      list ChatGPTCloud.ProcessIntelligence.Qualification, :qualifications, :read
      get ChatGPTCloud.ProcessIntelligence.CostObservation, :cost_observation, :read
      list ChatGPTCloud.ProcessIntelligence.CostObservation, :cost_observations, :read
    end
  end

  tools do
    tool :list_qualifications, ChatGPTCloud.ProcessIntelligence.Qualification, :read,
      description: "Read qualification evidence and bounded standing. This tool cannot actuate deployments."

    tool :list_cost_observations, ChatGPTCloud.ProcessIntelligence.CostObservation, :read,
      description: "Read metering observations. Values are evidence, not billing authority."
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
    resource ChatGPTCloud.ProcessIntelligence.Qualification
    resource ChatGPTCloud.ProcessIntelligence.CostObservation
    resource ChatGPTCloud.ProcessIntelligence.SecretCredential
  end
end
