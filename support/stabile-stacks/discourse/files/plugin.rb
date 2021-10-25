# name: multiurl
# about: Allow Discourse to serve same site to multiple URLs
# version: 0.1
# author: Origo Systems ApS

after_initialize do

  module ::OverrideEnforceHostname
    def call(env)
      @app.call(env)
    end
  end

  class Middleware::EnforceHostname
    prepend OverrideEnforceHostname
  end

end
